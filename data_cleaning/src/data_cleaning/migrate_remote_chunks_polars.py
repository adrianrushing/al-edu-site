from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import adbc_driver_postgresql.dbapi as adbc_dbapi
import polars as pl


LOCAL_DATABASE_URL = "postgresql://dev_user:dev_password@127.0.0.1:5433/eflt"
CHECKPOINT_PATH = (
    Path(__file__).resolve().parents[2] / ".chunk_migration_checkpoints.json"
)
BATCH_SIZE = 20_000
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TableConfig:
    name: str
    key_columns: tuple[str, ...]
    bucket_column: str | None = None
    bucket_count: int = 1


TABLES: tuple[TableConfig, ...] = (
    TableConfig(
        name="core.fact_geo_population",
        key_columns=("geoid10", "year", "population_group"),
    ),
    TableConfig(
        name="core.fact_geo_opportunity",
        key_columns=("geoid10", "year", "metric_code", "norm_scope"),
    ),
    TableConfig(
        name="core.fact_teacher_experience",
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
        bucket_column="school_key",
        bucket_count=32,
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


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _table_sql_name(table_name: str) -> str:
    schema, table = table_name.split(".", 1)
    return f"{_quote_ident(schema)}.{_quote_ident(table)}"


def _where_clause(config: TableConfig, year: int, bucket: int | None) -> str:
    clauses = [f'"year" = {year}']
    if config.bucket_column is not None and bucket is not None:
        clauses.append(
            f"MOD({_quote_ident(config.bucket_column)}, {config.bucket_count}) = {bucket}"
        )
    return " AND ".join(clauses)


def _partition_tag(config: TableConfig, year: int, bucket: int | None) -> str:
    if config.bucket_column is None or bucket is None:
        return f"{config.name}|year={year}"
    return f"{config.name}|year={year}|bucket={bucket}"


def _load_checkpoint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"partitions": {}, "summary": {}}
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


def _read_count(
    connection: Any, config: TableConfig, year: int, bucket: int | None
) -> int:
    table_sql = _table_sql_name(config.name)
    where_clause = _where_clause(config, year, bucket)
    query = f"SELECT COUNT(*) AS c FROM {table_sql} WHERE {where_clause}"
    return int(_read_df(connection, query).item(0, 0))


def _read_local_partition(
    connection: Any, config: TableConfig, year: int, bucket: int | None
) -> pl.DataFrame:
    table_sql = _table_sql_name(config.name)
    where_clause = _where_clause(config, year, bucket)
    order_sql = ", ".join(_quote_ident(col) for col in config.key_columns)
    query = f"SELECT * FROM {table_sql} WHERE {where_clause} ORDER BY {order_sql}"
    return _read_df(connection, query)


def _read_remote_keys(
    connection: Any, config: TableConfig, year: int, bucket: int | None
) -> pl.DataFrame:
    table_sql = _table_sql_name(config.name)
    key_sql = ", ".join(_quote_ident(col) for col in config.key_columns)
    where_clause = _where_clause(config, year, bucket)
    query = f"SELECT {key_sql} FROM {table_sql} WHERE {where_clause}"
    key_df = _read_df(connection, query)
    if key_df.height == 0:
        return key_df
    return key_df.unique(subset=list(config.key_columns), maintain_order=False)


def _table_column_types(connection: Any, table_name: str) -> dict[str, str]:
    schema, table = table_name.split(".", 1)
    query = (
        "SELECT column_name, data_type "
        "FROM information_schema.columns "
        f"WHERE table_schema = '{schema}' AND table_name = '{table}' "
        "ORDER BY ordinal_position"
    )
    df = _read_df(connection, query)
    if df.height == 0:
        raise RuntimeError(f"No columns found for remote table {table_name}")

    columns = df.get_column("column_name").to_list()
    types = df.get_column("data_type").to_list()
    return {str(col): str(dtype) for col, dtype in zip(columns, types, strict=True)}


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
            continue

    if not cast_exprs:
        return df
    return df.with_columns(cast_exprs)


def _sync_partition(
    local_conn: Any,
    remote_conn: Any,
    remote_url: str,
    config: TableConfig,
    year: int,
    bucket: int | None,
    checkpoint: dict[str, Any],
    column_types: dict[str, str],
) -> None:
    partition_tag = _partition_tag(config, year, bucket)
    local_count = _read_count(local_conn, config, year, bucket)
    remote_count_before = _read_count(remote_conn, config, year, bucket)
    if local_count == 0:
        logger.info("partition_skip partition=%s reason=local_count_zero", partition_tag)
        return

    logger.info(
        "partition_start partition=%s local_count=%s remote_count_before=%s",
        partition_tag,
        local_count,
        remote_count_before,
    )

    logger.info("pull_start partition=%s", partition_tag)
    full_partition = _read_local_partition(local_conn, config, year, bucket)
    logger.info(
        "pull_done partition=%s pulled_rows=%s",
        partition_tag,
        full_partition.height,
    )

    if full_partition.height == 0:
        logger.info("partition_skip partition=%s reason=empty_pull", partition_tag)
        return

    full_partition = full_partition.unique(
        subset=list(config.key_columns), keep="first", maintain_order=True
    )

    remote_keys = _read_remote_keys(remote_conn, config, year, bucket)
    if remote_keys.height > 0:
        to_insert = full_partition.join(
            remote_keys,
            on=list(config.key_columns),
            how="anti",
        )
    else:
        to_insert = full_partition

    rows_to_insert = to_insert.height
    push_total = (rows_to_insert + BATCH_SIZE - 1) // BATCH_SIZE
    logger.info(
        "push_plan partition=%s total_chunks=%s rows_to_insert=%s batch_size=%s",
        partition_tag,
        push_total,
        rows_to_insert,
        BATCH_SIZE,
    )

    if rows_to_insert == 0:
        logger.info("partition_skip partition=%s reason=no_rows_to_insert", partition_tag)
        checkpoint["partitions"][partition_tag] = {
            "pulled": True,
            "rows_to_insert": 0,
            "completed_chunks": [],
        }
        _save_checkpoint(CHECKPOINT_PATH, checkpoint)
        return

    pushed_chunks: list[int] = (
        checkpoint["partitions"].get(partition_tag, {}).get("completed_chunks", [])
    )

    for slice_offset in range(0, rows_to_insert, BATCH_SIZE):
        push_index = slice_offset // BATCH_SIZE
        display_chunk = push_index + 1

        if push_index in pushed_chunks:
            logger.info(
                "chunk_skip partition=%s chunk=%s/%s reason=checkpoint",
                partition_tag,
                display_chunk,
                push_total,
            )
            continue

        batch = to_insert.slice(slice_offset, BATCH_SIZE)
        prepared = _prepare_for_write(batch, column_types)
        prepared.write_database(
            table_name=config.name,
            connection=remote_url,
            if_table_exists="append",
            engine="adbc",
        )

        pushed_chunks.append(push_index)
        checkpoint["partitions"][partition_tag] = {
            "pulled": True,
            "rows_to_insert": rows_to_insert,
            "completed_chunks": pushed_chunks,
        }
        _save_checkpoint(CHECKPOINT_PATH, checkpoint)

        logger.info(
            "push_done partition=%s chunk=%s/%s source_rows=%s inserted_rows=%s",
            partition_tag,
            display_chunk,
            push_total,
            batch.height,
            batch.height,
        )

    remote_count_after = _read_count(remote_conn, config, year, bucket)
    logger.info(
        "partition_complete partition=%s remote_count_after=%s",
        partition_tag,
        remote_count_after,
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    remote_url = _load_remote_database_url()
    checkpoint = _load_checkpoint(CHECKPOINT_PATH)

    with adbc_dbapi.connect(LOCAL_DATABASE_URL) as local_conn:
        with adbc_dbapi.connect(remote_url) as remote_conn:
            for config in TABLES:
                years = _read_years(local_conn, config)
                column_types = _table_column_types(remote_conn, config.name)
                logger.info("table_start table=%s years=%s", config.name, years)

                for year in years:
                    if config.bucket_column is None:
                        _sync_partition(
                            local_conn,
                            remote_conn,
                            remote_url,
                            config,
                            year,
                            None,
                            checkpoint,
                            column_types,
                        )
                        continue

                    for bucket in range(config.bucket_count):
                        _sync_partition(
                            local_conn,
                            remote_conn,
                            remote_url,
                            config,
                            year,
                            bucket,
                            checkpoint,
                            column_types,
                        )

    logger.info("checkpoint_file=%s", CHECKPOINT_PATH)
    logger.info("migration_complete=true")


if __name__ == "__main__":
    main()
