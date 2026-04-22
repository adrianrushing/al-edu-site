from __future__ import annotations

import argparse
import csv
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import psycopg

DEFAULT_SOURCE_DIR = Path(__file__).resolve().parent / "downloaded"
DEFAULT_BATCH_SIZE = 20_000
DEFAULT_REMOTE_DATABASE_URL = "postgresql://eflt_etl:1qaz2wsx3edc@127.0.0.1:15432/eflt"

SOURCE_COLUMNS = (
    "Year",
    "System",
    "School",
    "Gender",
    "Race",
    "Ethnicity",
    "Sub Population",
    "Demographic Count",
    "Total Count",
    "Demographic Rate",
)

TARGET_COLUMNS = (
    "year",
    "system",
    "school",
    "gender",
    "race",
    "ethnicity",
    "sub_population",
    "demographic_count",
    "total_count",
    "demographic_rate",
    "_source_file",
    "_ingested_at",
)

UNIQUE_COLUMNS = TARGET_COLUMNS[:-2]
FILE_PREFIX = "alsde_educator_demographics_"

logger = logging.getLogger(__name__)


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def _load_remote_database_url(cli_value: str | None) -> str:
    if cli_value:
        return cli_value.strip().strip('"')

    env_value = os.getenv("REMOTE_DATABASE_URL") or os.getenv("DATABASE_URL")
    if env_value:
        return env_value.strip().strip('"')

    root_env_path = Path(__file__).resolve().parents[5] / ".env"
    if root_env_path.exists():
        for line in root_env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip('"')

    return DEFAULT_REMOTE_DATABASE_URL


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


def _ensure_target_table(conn: psycopg.Connection) -> None:
    ddl = """
    CREATE SCHEMA IF NOT EXISTS staging;
    CREATE TABLE IF NOT EXISTS staging.stg_teacher_demographics (
        year TEXT,
        system TEXT,
        school TEXT,
        gender TEXT,
        race TEXT,
        ethnicity TEXT,
        sub_population TEXT,
        demographic_count TEXT,
        total_count TEXT,
        demographic_rate TEXT,
        _source_file TEXT,
        _ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def _dedup_existing_rows(conn: psycopg.Connection) -> None:
    partition = ", ".join(UNIQUE_COLUMNS)
    dedup_sql = f"""
    DELETE FROM staging.stg_teacher_demographics t
    USING (
        SELECT ctid,
               ROW_NUMBER() OVER (
                   PARTITION BY {partition}
                   ORDER BY _ingested_at, ctid
               ) AS rn
        FROM staging.stg_teacher_demographics
    ) d
    WHERE t.ctid = d.ctid
      AND d.rn > 1;
    """
    with conn.cursor() as cur:
        cur.execute(dedup_sql)
    conn.commit()


def _ensure_unique_index(conn: psycopg.Connection) -> None:
    index_sql = """
    CREATE UNIQUE INDEX IF NOT EXISTS stg_teacher_demographics_unique_idx
    ON staging.stg_teacher_demographics (
        year, system, school, gender, race, ethnicity, sub_population,
        demographic_count, total_count, demographic_rate
    );
    """
    with conn.cursor() as cur:
        cur.execute(index_sql)
    conn.commit()


def _iter_yearly_files(source_dir: Path) -> list[Path]:
    files = []
    for file_path in sorted(source_dir.glob(f"{FILE_PREFIX}*.csv")):
        suffix = file_path.stem.removeprefix(FILE_PREFIX)
        if len(suffix) == 9 and suffix[4] == "-":
            files.append(file_path)
    return files


def _normalize_row(
    row: dict[str, str], source_file: str, ingested_at: datetime
) -> tuple[str | None, ...]:
    values: list[str | None] = []
    for key in SOURCE_COLUMNS:
        raw = row.get(key)
        values.append(raw.strip() if isinstance(raw, str) else raw)
    values.append(source_file)
    values.append(ingested_at.isoformat())
    return tuple(values)


def _copy_to_temp(conn: psycopg.Connection, rows: list[tuple[str | None, ...]]) -> None:
    copy_sql = (
        "COPY staging.tmp_stg_teacher_demographics_load ("
        + ", ".join(TARGET_COLUMNS)
        + ") FROM STDIN"
    )
    with conn.cursor() as cur:
        with cur.copy(copy_sql) as copy:
            for row in rows:
                copy.write_row(row)


def _flush_batch(conn: psycopg.Connection, batch: list[tuple[str | None, ...]]) -> int:
    if not batch:
        return 0

    _copy_to_temp(conn, batch)
    insert_sql = f"""
        INSERT INTO staging.stg_teacher_demographics ({", ".join(TARGET_COLUMNS)})
        SELECT DISTINCT {", ".join(TARGET_COLUMNS)}
        FROM staging.tmp_stg_teacher_demographics_load
        ON CONFLICT ({", ".join(UNIQUE_COLUMNS)}) DO NOTHING;
    """
    with conn.cursor() as cur:
        cur.execute(insert_sql)
        inserted = cur.rowcount or 0
        cur.execute("TRUNCATE staging.tmp_stg_teacher_demographics_load;")
    conn.commit()
    return inserted


def _load_file(conn: psycopg.Connection, file_path: Path, batch_size: int) -> None:
    logger.info("load_start file=%s", file_path.name)
    seen_rows = 0
    inserted_rows = 0
    batch: list[tuple[str | None, ...]] = []

    with file_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            logger.warning("file_skip file=%s reason=no_headers", file_path.name)
            return

        missing = sorted(
            set(str(name) for name in SOURCE_COLUMNS) - set(reader.fieldnames)
        )
        if missing:
            raise RuntimeError(f"Missing expected columns in {file_path.name}: {missing}")

        for row in reader:
            batch.append(
                _normalize_row(
                    row=row,
                    source_file=file_path.name,
                    ingested_at=datetime.now(UTC),
                )
            )
            seen_rows += 1
            if len(batch) >= batch_size:
                inserted_rows += _flush_batch(conn, batch)
                batch = []

    inserted_rows += _flush_batch(conn, batch)
    logger.info(
        "load_complete file=%s seen_rows=%s inserted_rows=%s",
        file_path.name,
        seen_rows,
        inserted_rows,
    )


def run_load(source_dir: Path, database_url: str, batch_size: int) -> None:
    files = _iter_yearly_files(source_dir)
    if not files:
        raise RuntimeError(f"No yearly teacher demographics files found in {source_dir}")

    with psycopg.connect(
        conninfo=database_url,
        options="-c idle_in_transaction_session_timeout=30000",
        autocommit=False,
    ) as conn:
        _ensure_target_table(conn)
        _dedup_existing_rows(conn)
        _ensure_unique_index(conn)

        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS staging.tmp_stg_teacher_demographics_load;")
            cur.execute(
                """
                CREATE TABLE staging.tmp_stg_teacher_demographics_load
                (LIKE staging.stg_teacher_demographics INCLUDING DEFAULTS);
                """
            )
        conn.commit()

        for file_path in files:
            _load_file(conn=conn, file_path=file_path, batch_size=batch_size)

        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS staging.tmp_stg_teacher_demographics_load;")
        conn.commit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Load combined ALSDE teacher demographics yearly CSV files into "
            "staging.stg_teacher_demographics with deduplicated inserts."
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

    remote_url = _with_keepalive_params(_load_remote_database_url(args.database_url))
    logger.info("remote_target=%s", remote_url)
    logger.info("source_dir=%s", source_dir)
    run_load(source_dir=source_dir, database_url=remote_url, batch_size=args.batch_size)
    logger.info("teacher_demographics_remote_load_complete=true")


if __name__ == "__main__":
    main()
