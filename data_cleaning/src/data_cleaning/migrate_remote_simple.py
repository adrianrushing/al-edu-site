from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import adbc_driver_postgresql.dbapi as adbc_dbapi
import polars as pl
import psycopg


LOCAL_DATABASE_URL = "postgresql://dev_user:dev_password@127.0.0.1:5433/eflt"
CHECKPOINT_PATH = (
    Path(__file__).resolve().parents[2] / ".migration_checkpoints_simple.json"
)
BATCH_SIZE = 20_000
CHUNK_SLEEP_SECONDS = float(os.getenv("MIGRATE_CHUNK_SLEEP_SECONDS", "0.1"))
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TableConfig:
    name: str
    key_columns: tuple[str, ...]


TABLES: tuple[TableConfig, ...] = (
    TableConfig(
        name="core.fact_teacher_demographics",
        key_columns=(
            "school_key",
            "year",
            "gender",
            "race",
            "ethnicity",
            "sub_population",
        ),
    ),
    TableConfig(
        name="core.fact_accountability",
        key_columns=(
            "school_key",
            "year",
            "indicator",
            "grade",
            "gender",
            "race",
            "ethnicity",
            "sub_population",
        ),
    ),
    TableConfig(
        name="sandbox.fact_teacher_demographics_long_review",
        key_columns=(
            "year",
            "dist_name",
            "school_name",
            "gender",
            "race",
            "ethnicity",
            "sub_population",
        ),
    ),
    TableConfig(
        name="core.fact_student_demographics",
        key_columns=(
            "school_key",
            "year",
            "grade",
            "gender",
            "ethnicity",
            "race",
            "sub_population",
        ),
    ),
)


def _load_remote_database_url() -> str:
    env_value = os.getenv("DATABASE_URL")
    if env_value:
        return env_value.strip().strip('"')

    root_env_path = Path(__file__).resolve().parents[3] / ".env"
    if not root_env_path.exists():
        raise RuntimeError("Remote DATABASE_URL not found in env or root .env")

    for line in root_env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip().strip('"')

    raise RuntimeError("DATABASE_URL not found in root .env")


def _with_keepalive_params(remote_url: str) -> str:
    parts = urlsplit(remote_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update(
        {
            "keepalives": "1",
            "keepalives_idle": "30",
            "keepalives_interval": "10",
            "keepalives_count": "5",
        }
    )
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _table_sql_name(table_name: str) -> str:
    schema, table = table_name.split(".", 1)
    return f"{_quote_ident(schema)}.{_quote_ident(table)}"


def _partition_tag(table_name: str, year: int) -> str:
    return f"{table_name}|year={year}"


def _load_checkpoint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"partitions": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_checkpoint(path: Path, data: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, indent=4, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


def _read_df(connection: Any, query: str) -> pl.DataFrame:
    return pl.read_database(query=query, connection=connection)


def _read_years(connection: Any, config: TableConfig) -> list[int]:
    table_sql = _table_sql_name(config.name)
    query = (
        f'SELECT DISTINCT "year" FROM {table_sql} '
        f'WHERE "year" IS NOT NULL ORDER BY "year"'
    )
    years_df = _read_df(connection, query)
    return [int(value) for value in years_df.get_column("year").to_list()]


def _read_partition(connection: Any, config: TableConfig, year: int) -> pl.DataFrame:
    table_sql = _table_sql_name(config.name)
    order_sql = ", ".join(_quote_ident(col) for col in config.key_columns)
    query = f'SELECT * FROM {table_sql} WHERE "year" = {year} ORDER BY {order_sql}'
    return _read_df(connection, query)


def _table_column_types(remote_url: str, table_name: str) -> dict[str, str]:
    schema, table = table_name.split(".", 1)
    query = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
    """

    with psycopg.connect(
        conninfo=_with_keepalive_params(remote_url),
        options="-c idle_in_transaction_session_timeout=30000",
        autocommit=True,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(query, (schema, table))
            rows = cur.fetchall()

    if not rows:
        raise RuntimeError(f"No columns found for remote table {table_name}")
    return {str(col): str(dtype) for col, dtype in rows}


def _prepare_for_write(df: pl.DataFrame, column_types: dict[str, str]) -> pl.DataFrame:
    cast_exprs: list[pl.Expr] = []

    for col_name in df.columns:
        target_type = column_types.get(col_name)
        if target_type is None:
            continue

        if target_type in {"text", "character varying", "character"}:
            cast_exprs.append(
                pl.col(col_name).cast(pl.String, strict=False).alias(col_name)
            )
            continue

        cleaned = (
            pl.col(col_name)
            .cast(pl.String, strict=False)
            .str.strip_chars()
            .str.replace_all(",", "")
        )
        nullable = (
            pl.when(cleaned.is_null() | (cleaned == "")).then(None).otherwise(cleaned)
        )

        if target_type == "smallint":
            cast_exprs.append(nullable.cast(pl.Int16, strict=False).alias(col_name))
            continue
        if target_type == "integer":
            cast_exprs.append(nullable.cast(pl.Int32, strict=False).alias(col_name))
            continue
        if target_type == "bigint":
            cast_exprs.append(nullable.cast(pl.Int64, strict=False).alias(col_name))
            continue
        if target_type == "numeric":
            cast_exprs.append(
                nullable.cast(pl.Decimal(precision=28, scale=6), strict=False).alias(
                    col_name
                )
            )
            continue
        if target_type in {"double precision", "real"}:
            cast_exprs.append(nullable.cast(pl.Float64, strict=False).alias(col_name))
            continue
        if target_type == "boolean":
            lowered = nullable.str.to_lowercase()
            as_bool = (
                pl.when(lowered.is_in(["t", "true", "1", "y", "yes"]))
                .then(True)
                .when(lowered.is_in(["f", "false", "0", "n", "no"]))
                .then(False)
                .otherwise(None)
            )
            cast_exprs.append(as_bool.alias(col_name))

    if not cast_exprs:
        return df
    return df.with_columns(cast_exprs)


def _migrate_year(
    local_conn: Any,
    remote_url: str,
    config: TableConfig,
    year: int,
    checkpoint: dict[str, Any],
    column_types: dict[str, str],
) -> None:
    tag = _partition_tag(config.name, year)
    logger.info("pull_start partition=%s", tag)
    pulled = _read_partition(local_conn, config, year)
    logger.info("pull_done partition=%s pulled_rows=%s", tag, pulled.height)

    if pulled.height == 0:
        logger.info("partition_skip partition=%s reason=empty_pull", tag)
        return

    total_chunks = (pulled.height + BATCH_SIZE - 1) // BATCH_SIZE
    logger.info(
        "push_plan partition=%s total_chunks=%s batch_size=%s",
        tag,
        total_chunks,
        BATCH_SIZE,
    )

    partition_state = checkpoint["partitions"].get(tag, {})
    completed_chunks = set(partition_state.get("completed_chunks", []))

    for chunk_idx in range(total_chunks):
        display_chunk = chunk_idx + 1
        if chunk_idx in completed_chunks:
            logger.info(
                "chunk_skip partition=%s chunk=%s/%s reason=checkpoint",
                tag,
                display_chunk,
                total_chunks,
            )
            continue

        batch = pulled.slice(chunk_idx * BATCH_SIZE, BATCH_SIZE)
        prepared = _prepare_for_write(batch, column_types)
        prepared.write_database(
            table_name=config.name,
            connection=remote_url,
            if_table_exists="append",
            engine="adbc",
        )
        if CHUNK_SLEEP_SECONDS > 0:
            time.sleep(CHUNK_SLEEP_SECONDS)

        completed_chunks.add(chunk_idx)
        checkpoint["partitions"][tag] = {
            "pulled_rows": pulled.height,
            "completed_chunks": sorted(completed_chunks),
        }
        _save_checkpoint(CHECKPOINT_PATH, checkpoint)

        logger.info(
            "push_done partition=%s chunk=%s/%s source_rows=%s inserted_rows=%s",
            tag,
            display_chunk,
            total_chunks,
            batch.height,
            batch.height,
        )

    logger.info("partition_complete partition=%s", tag)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    remote_url = _load_remote_database_url()
    checkpoint = _load_checkpoint(CHECKPOINT_PATH)

    with adbc_dbapi.connect(LOCAL_DATABASE_URL) as local_conn:
        for config in TABLES:
            years = _read_years(local_conn, config)
            column_types = _table_column_types(remote_url, config.name)
            logger.info("table_start table=%s years=%s", config.name, years)

            for year in years:
                _migrate_year(
                    local_conn,
                    remote_url,
                    config,
                    year,
                    checkpoint,
                    column_types,
                )

    logger.info("checkpoint_file=%s", CHECKPOINT_PATH)
    logger.info("migration_complete=true")


if __name__ == "__main__":
    main()
