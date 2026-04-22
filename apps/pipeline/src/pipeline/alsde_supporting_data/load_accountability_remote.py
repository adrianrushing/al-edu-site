from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import psycopg

DEFAULT_SOURCE_DIR = Path(__file__).resolve().parent / "downloaded"
DEFAULT_FILE_PATTERN = "*_Accountability.csv"
DEFAULT_BATCH_SIZE = 20_000
DEFAULT_REMOTE_DATABASE_URL = "postgresql://eflt_etl:1qaz2wsx3edc@127.0.0.1:15432/eflt"
CHECKPOINT_PATH = (
    Path(__file__).resolve().parents[3] / ".accountability_remote_load_checkpoints.json"
)
CHUNK_SLEEP_SECONDS = float(os.getenv("MIGRATE_CHUNK_SLEEP_SECONDS", "0.1"))

RAW_COLUMNS = (
    "year",
    "system",
    "school",
    "indicator",
    "grade",
    "gender",
    "race",
    "ethnicity",
    "sub_population",
    "score",
)

TARGET_COLUMNS = RAW_COLUMNS + ("_source_file", "_ingested_at")

logger = logging.getLogger(__name__)


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def _normalize_column_name(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


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


def _load_checkpoint(path: Path) -> dict[str, dict[str, dict[str, list[int] | int]]]:
    if not path.exists():
        return {"files": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_checkpoint(
    path: Path, data: dict[str, dict[str, dict[str, list[int] | int]]]
) -> None:
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, indent=4, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


def _ensure_target_table(conn: psycopg.Connection) -> None:
    ddl = """
    CREATE SCHEMA IF NOT EXISTS staging;
    CREATE TABLE IF NOT EXISTS staging.stg_school_accountability (
        year TEXT,
        system TEXT,
        school TEXT,
        indicator TEXT,
        grade TEXT,
        gender TEXT,
        race TEXT,
        ethnicity TEXT,
        sub_population TEXT,
        score TEXT,
        _source_file TEXT,
        _ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def _normalize_row(
    row: dict[str, str],
    field_map: dict[str, str],
    source_file: str,
    ingested_at: datetime,
) -> tuple[str | None, ...]:
    normalized = {
        _normalize_column_name(raw_key): value
        for raw_key, value in row.items()
        if raw_key
    }
    values: list[str | None] = []
    for key in RAW_COLUMNS:
        source_key = field_map[key]
        raw_value = normalized.get(source_key)
        values.append(raw_value if raw_value is not None else None)
    values.append(source_file)
    values.append(ingested_at.isoformat())
    return tuple(values)


def _write_chunk(conn: psycopg.Connection, rows: list[tuple[str | None, ...]]) -> None:
    copy_sql = (
        "COPY staging.stg_school_accountability ("
        + ", ".join(TARGET_COLUMNS)
        + ") FROM STDIN"
    )
    with conn.cursor() as cur:
        with cur.copy(copy_sql) as copy:
            for row in rows:
                copy.write_row(row)
    conn.commit()


def _validate_headers(raw_headers: list[str]) -> dict[str, str]:
    normalized_headers = {_normalize_column_name(name) for name in raw_headers}
    missing = sorted(set(RAW_COLUMNS) - normalized_headers)
    if missing:
        raise RuntimeError(f"Missing required headers after normalization: {missing}")
    return {name: name for name in RAW_COLUMNS}


def _load_file(
    conn: psycopg.Connection,
    file_path: Path,
    batch_size: int,
    checkpoint: dict[str, dict[str, dict[str, list[int] | int]]],
) -> None:
    file_tag = file_path.name
    file_state = checkpoint["files"].get(file_tag, {})
    completed_chunks = set(file_state.get("completed_chunks", []))

    logger.info("pull_start file=%s", file_tag)
    chunk_index = 0
    pushed_rows = 0
    seen_rows = 0

    with file_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            logger.warning("file_skip file=%s reason=no_headers", file_tag)
            return

        field_map = _validate_headers(reader.fieldnames)
        batch: list[tuple[str | None, ...]] = []
        chunk_started_at = datetime.now(UTC)

        for row in reader:
            batch.append(_normalize_row(row, field_map, file_tag, chunk_started_at))
            seen_rows += 1

            if len(batch) < batch_size:
                continue

            if chunk_index in completed_chunks:
                logger.info(
                    "chunk_skip file=%s chunk=%s reason=checkpoint",
                    file_tag,
                    chunk_index + 1,
                )
            else:
                _write_chunk(conn, batch)
                if CHUNK_SLEEP_SECONDS > 0:
                    time.sleep(CHUNK_SLEEP_SECONDS)
                completed_chunks.add(chunk_index)
                pushed_rows += len(batch)
                checkpoint["files"][file_tag] = {
                    "seen_rows": seen_rows,
                    "completed_chunks": sorted(completed_chunks),
                }
                _save_checkpoint(CHECKPOINT_PATH, checkpoint)
                logger.info(
                    "push_done file=%s chunk=%s rows=%s",
                    file_tag,
                    chunk_index + 1,
                    len(batch),
                )

            chunk_index += 1
            batch = []
            chunk_started_at = datetime.now(UTC)

        if batch:
            if chunk_index in completed_chunks:
                logger.info(
                    "chunk_skip file=%s chunk=%s reason=checkpoint",
                    file_tag,
                    chunk_index + 1,
                )
            else:
                _write_chunk(conn, batch)
                if CHUNK_SLEEP_SECONDS > 0:
                    time.sleep(CHUNK_SLEEP_SECONDS)
                completed_chunks.add(chunk_index)
                pushed_rows += len(batch)
                checkpoint["files"][file_tag] = {
                    "seen_rows": seen_rows,
                    "completed_chunks": sorted(completed_chunks),
                }
                _save_checkpoint(CHECKPOINT_PATH, checkpoint)
                logger.info(
                    "push_done file=%s chunk=%s rows=%s",
                    file_tag,
                    chunk_index + 1,
                    len(batch),
                )

    logger.info(
        "file_complete file=%s seen_rows=%s inserted_rows=%s completed_chunks=%s",
        file_tag,
        seen_rows,
        pushed_rows,
        len(completed_chunks),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Load ALSDE accountability CSV exports directly into "
            "remote staging.stg_school_accountability with chunked inserts."
        )
    )
    parser.add_argument(
        "--source-dir",
        default=str(DEFAULT_SOURCE_DIR),
        help=f"CSV directory (default: {DEFAULT_SOURCE_DIR})",
    )
    parser.add_argument(
        "--file-pattern",
        default=DEFAULT_FILE_PATTERN,
        help=f"Glob pattern for CSV files (default: {DEFAULT_FILE_PATTERN})",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help=(
            "Remote PostgreSQL URL. Defaults to REMOTE_DATABASE_URL, "
            "DATABASE_URL, root .env DATABASE_URL, then built-in port 15432 URL."
        ),
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


def run_load(
    source_dir: Path,
    file_pattern: str,
    database_url: str,
    batch_size: int,
) -> None:
    if not source_dir.exists():
        raise RuntimeError(f"Source directory does not exist: {source_dir}")

    files = sorted(source_dir.glob(file_pattern))
    if not files:
        raise RuntimeError(f"No files matched pattern {file_pattern!r} in {source_dir}")

    remote_url = _with_keepalive_params(database_url)
    checkpoint = _load_checkpoint(CHECKPOINT_PATH)

    logger.info("remote_target=%s", remote_url)
    logger.info("source_dir=%s matched_files=%s", source_dir, len(files))
    logger.info("checkpoint_file=%s", CHECKPOINT_PATH)

    with psycopg.connect(
        conninfo=remote_url,
        options="-c idle_in_transaction_session_timeout=30000",
        autocommit=False,
    ) as conn:
        _ensure_target_table(conn)

        for file_path in files:
            _load_file(
                conn=conn,
                file_path=file_path,
                batch_size=batch_size,
                checkpoint=checkpoint,
            )

    logger.info("remote_load_complete=true")


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)
    run_load(
        source_dir=Path(args.source_dir).resolve(),
        file_pattern=args.file_pattern,
        database_url=_load_remote_database_url(args.database_url),
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
