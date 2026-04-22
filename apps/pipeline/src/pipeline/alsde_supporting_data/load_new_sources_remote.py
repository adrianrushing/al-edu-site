from __future__ import annotations

import argparse
import csv
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import psycopg

from pipeline.alsde_supporting_data.load_accountability_remote import (
    _load_remote_database_url,
    _with_keepalive_params,
)

DEFAULT_SOURCE_DIR = Path(__file__).resolve().parent / "downloaded"
DEFAULT_BATCH_SIZE = 20_000
DEFAULT_EXPECTED_PORT = 15432

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatasetConfig:
    name: str
    file_prefix: str
    table_name: str
    source_columns: tuple[str, ...]
    target_columns: tuple[str, ...]

    @property
    def unique_columns(self) -> tuple[str, ...]:
        return self.target_columns[:-2]

    @property
    def temp_table_name(self) -> str:
        return f"staging.tmp_{self.table_name.split('.', 1)[1]}_load"


EDUCATOR_CREDENTIALS = DatasetConfig(
    name="educator_credentials",
    file_prefix="alsde_educator_credentials_",
    table_name="staging.stg_educator_credentials",
    source_columns=(
        "Year",
        "System",
        "School",
        "Gender",
        "Race",
        "Ethnicity",
        "Sub Population",
        "Degree Type",
        "Credential Count",
        "Total Count",
        "Credential Rate",
    ),
    target_columns=(
        "year",
        "system",
        "school",
        "gender",
        "race",
        "ethnicity",
        "sub_population",
        "degree_type",
        "credential_count",
        "total_count",
        "credential_rate",
        "_source_file",
        "_ingested_at",
    ),
)

GRADUATION_RATE = DatasetConfig(
    name="graduation_rate",
    file_prefix="alsde_graduation_rate_",
    table_name="staging.stg_graduation_rate",
    source_columns=(
        "Year",
        "Sub Population",
        "System",
        "School",
        "Grade",
        "Gender",
        "Race",
        "Ethnicity",
        "Student Count",
        "Graduates",
        "Graduation %",
        "CCR Attainment",
        "CCR Attainment %",
    ),
    target_columns=(
        "year",
        "sub_population",
        "system",
        "school",
        "grade",
        "gender",
        "race",
        "ethnicity",
        "student_count",
        "graduates",
        "graduation_percent",
        "ccr_attainment",
        "ccr_attainment_percent",
        "_source_file",
        "_ingested_at",
    ),
)

DATASETS: tuple[DatasetConfig, ...] = (EDUCATOR_CREDENTIALS, GRADUATION_RATE)


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def _iter_yearly_files(source_dir: Path, file_prefix: str) -> list[Path]:
    files = []
    for file_path in sorted(source_dir.glob(f"{file_prefix}*.csv")):
        suffix = file_path.stem.removeprefix(file_prefix)
        if len(suffix) == 9 and suffix[4] == "-":
            files.append(file_path)
    return files


def _assert_connection_port(database_url: str, expected_port: int) -> None:
    parsed = urlsplit(database_url)
    conn_port = parsed.port
    if conn_port != expected_port:
        raise RuntimeError(
            f"Refusing to load: URL port {conn_port}, expected {expected_port}"
        )


def _log_remote_identity(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT inet_server_addr(), inet_server_port(), "
            "current_database(), current_user"
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("Failed to query remote server metadata")
        server_addr, server_port, db_name, db_user = row

    logger.info(
        "remote_verified addr=%s port=%s db=%s user=%s",
        server_addr,
        server_port,
        db_name,
        db_user,
    )


def _ensure_target_table(conn: psycopg.Connection, config: DatasetConfig) -> None:
    columns_sql = ",\n        ".join(f"{col} TEXT" for col in config.target_columns[:-2])
    ddl = f"""
    CREATE SCHEMA IF NOT EXISTS staging;
    CREATE TABLE IF NOT EXISTS {config.table_name} (
        {columns_sql},
        _source_file TEXT,
        _ingested_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
    );
    """
    with conn.cursor() as cur:
        cur_any: Any = cur
        cur_any.execute(ddl)
    conn.commit()


def _dedup_existing_rows(conn: psycopg.Connection, config: DatasetConfig) -> None:
    partition = ", ".join(config.unique_columns)
    dedup_sql = f"""
    DELETE FROM {config.table_name} t
    USING (
        SELECT ctid,
               ROW_NUMBER() OVER (
                   PARTITION BY {partition}
                   ORDER BY _ingested_at, ctid
               ) AS rn
        FROM {config.table_name}
    ) d
    WHERE t.ctid = d.ctid
      AND d.rn > 1;
    """
    with conn.cursor() as cur:
        cur_any: Any = cur
        cur_any.execute(dedup_sql)
    conn.commit()


def _ensure_unique_index(conn: psycopg.Connection, config: DatasetConfig) -> None:
    table_short = config.table_name.split(".", 1)[1]
    index_name = f"{table_short}_unique_idx"
    index_cols = ", ".join(config.unique_columns)
    index_sql = f"""
    CREATE UNIQUE INDEX IF NOT EXISTS {index_name}
    ON {config.table_name} ({index_cols});
    """
    with conn.cursor() as cur:
        cur_any: Any = cur
        cur_any.execute(index_sql)
    conn.commit()


def _normalize_row(
    row: dict[str, str], config: DatasetConfig, source_file: str, ingested_at: datetime
) -> tuple[str | None, ...]:
    values: list[str | None] = []
    for key in config.source_columns:
        raw = row.get(key)
        values.append(raw.strip() if isinstance(raw, str) else raw)
    values.append(source_file)
    values.append(ingested_at.isoformat())
    return tuple(values)


def _copy_to_temp(
    conn: psycopg.Connection, config: DatasetConfig, rows: list[tuple[str | None, ...]]
) -> None:
    copy_sql = (
        f"COPY {config.temp_table_name} ({', '.join(config.target_columns)}) FROM STDIN"
    )
    with conn.cursor() as cur:
        cur_any: Any = cur
        with cur_any.copy(copy_sql) as copy:
            for row in rows:
                copy.write_row(row)


def _flush_batch(
    conn: psycopg.Connection, config: DatasetConfig, batch: list[tuple[str | None, ...]]
) -> int:
    if not batch:
        return 0

    _copy_to_temp(conn, config, batch)
    insert_sql = f"""
        INSERT INTO {config.table_name} ({", ".join(config.target_columns)})
        SELECT DISTINCT {", ".join(config.target_columns)}
        FROM {config.temp_table_name}
        ON CONFLICT ({", ".join(config.unique_columns)}) DO NOTHING;
    """
    with conn.cursor() as cur:
        cur_any: Any = cur
        cur_any.execute(insert_sql)
        inserted = cur_any.rowcount or 0
        cur_any.execute(f"TRUNCATE {config.temp_table_name};")
    conn.commit()
    return inserted


def _load_file(
    conn: psycopg.Connection, config: DatasetConfig, file_path: Path, batch_size: int
) -> None:
    logger.info("load_start dataset=%s file=%s", config.name, file_path.name)
    seen_rows = 0
    inserted_rows = 0
    batch: list[tuple[str | None, ...]] = []

    with file_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            logger.warning("file_skip file=%s reason=no_headers", file_path.name)
            return

        missing = sorted(set(config.source_columns) - set(reader.fieldnames))
        if missing:
            raise RuntimeError(f"Missing expected columns in {file_path.name}: {missing}")

        for row in reader:
            batch.append(
                _normalize_row(
                    row=row,
                    config=config,
                    source_file=file_path.name,
                    ingested_at=datetime.now(UTC),
                )
            )
            seen_rows += 1
            if len(batch) >= batch_size:
                inserted_rows += _flush_batch(conn, config, batch)
                batch = []

    inserted_rows += _flush_batch(conn, config, batch)
    logger.info(
        "load_complete dataset=%s file=%s seen_rows=%s inserted_rows=%s",
        config.name,
        file_path.name,
        seen_rows,
        inserted_rows,
    )


def _prepare_temp_table(conn: psycopg.Connection, config: DatasetConfig) -> None:
    with conn.cursor() as cur:
        cur_any: Any = cur
        cur_any.execute(f"DROP TABLE IF EXISTS {config.temp_table_name};")
        cur_any.execute(
            f"CREATE TABLE {config.temp_table_name} "
            f"(LIKE {config.table_name} INCLUDING DEFAULTS);"
        )
    conn.commit()


def _drop_temp_table(conn: psycopg.Connection, config: DatasetConfig) -> None:
    with conn.cursor() as cur:
        cur_any: Any = cur
        cur_any.execute(f"DROP TABLE IF EXISTS {config.temp_table_name};")
    conn.commit()


def run_load(
    source_dir: Path,
    database_url: str,
    batch_size: int,
    expected_port: int,
    datasets: tuple[DatasetConfig, ...],
) -> None:
    _assert_connection_port(database_url, expected_port)

    with psycopg.connect(
        conninfo=database_url,
        options="-c idle_in_transaction_session_timeout=30000",
        autocommit=False,
    ) as conn:
        _log_remote_identity(conn)

        for config in datasets:
            files = _iter_yearly_files(source_dir, config.file_prefix)
            if not files:
                raise RuntimeError(
                    f"No yearly files found for {config.name} in {source_dir}"
                )

            _ensure_target_table(conn, config)
            _dedup_existing_rows(conn, config)
            _ensure_unique_index(conn, config)
            _prepare_temp_table(conn, config)

            try:
                for file_path in files:
                    _load_file(
                        conn=conn,
                        config=config,
                        file_path=file_path,
                        batch_size=batch_size,
                    )
            finally:
                _drop_temp_table(conn, config)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Load ALSDE new source families (educator credentials + graduation rate) "
            "into staging with deduplicated append behavior."
        )
    )
    parser.add_argument(
        "--source-dir",
        default=str(DEFAULT_SOURCE_DIR),
        help=f"CSV directory (default: {DEFAULT_SOURCE_DIR})",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Remote PostgreSQL URL.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Rows per chunk (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--expected-port",
        type=int,
        default=DEFAULT_EXPECTED_PORT,
        help=(f"Required connection URL port (default: {DEFAULT_EXPECTED_PORT})."),
    )
    parser.add_argument(
        "--datasets",
        nargs="*",
        default=["educator_credentials", "graduation_rate"],
        choices=["educator_credentials", "graduation_rate"],
        help="Optional subset of new source families to load.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)
    source_dir = Path(args.source_dir).resolve()
    if not source_dir.exists():
        raise RuntimeError(f"Source directory does not exist: {source_dir}")

    selected = tuple(cfg for cfg in DATASETS if cfg.name in set(args.datasets))
    remote_url = _with_keepalive_params(_load_remote_database_url(args.database_url))

    logger.info("remote_target=%s", remote_url)
    logger.info("source_dir=%s", source_dir)
    logger.info("datasets=%s", [cfg.name for cfg in selected])

    run_load(
        source_dir=source_dir,
        database_url=remote_url,
        batch_size=args.batch_size,
        expected_port=args.expected_port,
        datasets=selected,
    )
    logger.info("new_sources_staging_remote_load_complete=true")


if __name__ == "__main__":
    main()
