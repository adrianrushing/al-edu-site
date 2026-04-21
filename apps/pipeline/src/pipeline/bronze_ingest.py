from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from psycopg import Connection
from psycopg.types.json import Jsonb


RAW_SOURCE_LAYER = "flat_data/in/raw_data"


@dataclass(frozen=True)
class CsvSource:
    absolute_path: Path
    source_path: str
    dataset_key: str
    file_hash: str


@dataclass(frozen=True)
class IngestSummary:
    run_id: UUID
    source_count: int
    row_count: int
    started_at: datetime
    finished_at: datetime


def default_raw_data_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "flat_data" / "in" / "raw_data"


def _dataset_key(relative_path: Path) -> str:
    parent = relative_path.parent.as_posix()
    if parent == ".":
        return relative_path.stem
    return parent.replace("/", "_")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def discover_csv_sources(raw_data_dir: Path) -> list[CsvSource]:
    root = raw_data_dir.resolve()
    if not root.exists():
        raise FileNotFoundError(f"Raw data directory does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Raw data path is not a directory: {root}")

    repo_root = Path(__file__).resolve().parents[4]
    sources: list[CsvSource] = []
    for csv_path in sorted(root.rglob("*.csv")):
        source_abs = csv_path.resolve()
        try:
            source_path = source_abs.relative_to(repo_root).as_posix()
        except ValueError:
            source_path = source_abs.as_posix()

        relative_to_raw = source_abs.relative_to(root)
        sources.append(
            CsvSource(
                absolute_path=source_abs,
                source_path=source_path,
                dataset_key=_dataset_key(relative_to_raw),
                file_hash=_sha256(source_abs),
            )
        )

    return sources


def ensure_bronze_tables(conn: Connection) -> None:
    ddl = """
    CREATE SCHEMA IF NOT EXISTS bronze;

    CREATE TABLE IF NOT EXISTS bronze.raw_file_manifest (
        run_id UUID NOT NULL,
        source_path TEXT NOT NULL,
        source_layer TEXT NOT NULL,
        dataset_key TEXT NOT NULL,
        file_hash TEXT,
        row_count BIGINT,
        ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (run_id, source_path)
    );

    CREATE TABLE IF NOT EXISTS bronze.raw_csv_records (
        run_id UUID NOT NULL,
        source_path TEXT NOT NULL,
        dataset_key TEXT NOT NULL,
        row_number BIGINT NOT NULL,
        row_data JSONB NOT NULL,
        ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (run_id, source_path, row_number)
    );

    CREATE INDEX IF NOT EXISTS idx_bronze_raw_csv_records_run_id
        ON bronze.raw_csv_records (run_id);

    CREATE INDEX IF NOT EXISTS idx_bronze_raw_csv_records_dataset_key
        ON bronze.raw_csv_records (dataset_key);

    CREATE INDEX IF NOT EXISTS idx_bronze_raw_csv_records_source_path
        ON bronze.raw_csv_records (source_path);
    """
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def _normalize_row(row: dict[str, str | None]) -> dict[str, str | None]:
    normalized: dict[str, str | None] = {}
    for key, value in row.items():
        cleaned_key = key.strip() if key is not None else ""
        if cleaned_key == "":
            continue
        cleaned_value = value.strip() if isinstance(value, str) else value
        normalized[cleaned_key] = None if cleaned_value == "" else cleaned_value
    return normalized


def _ingest_source(conn: Connection, run_id: UUID, source: CsvSource) -> int:
    row_count = 0
    with conn.transaction():
        with conn.cursor() as cur:
            with source.absolute_path.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                with cur.copy(
                    """
                    COPY bronze.raw_csv_records
                    (run_id, source_path, dataset_key, row_number, row_data)
                    FROM STDIN
                    """
                ) as copy:
                    for row_number, row in enumerate(reader, start=1):
                        payload = _normalize_row(row)
                        copy.write_row(
                            (
                                run_id,
                                source.source_path,
                                source.dataset_key,
                                row_number,
                                Jsonb(payload),
                            )
                        )
                        row_count = row_number

            cur.execute(
                """
                INSERT INTO bronze.raw_file_manifest
                (run_id, source_path, source_layer, dataset_key, file_hash, row_count)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    run_id,
                    source.source_path,
                    RAW_SOURCE_LAYER,
                    source.dataset_key,
                    source.file_hash,
                    row_count,
                ),
            )

    return row_count


def ingest_csv_sources(conn: Connection, raw_data_dir: Path) -> IngestSummary:
    sources = discover_csv_sources(raw_data_dir)
    ensure_bronze_tables(conn)

    started_at = datetime.now(tz=UTC)
    run_id = uuid4()
    total_rows = 0
    for source in sources:
        total_rows += _ingest_source(conn, run_id, source)

    finished_at = datetime.now(tz=UTC)
    return IngestSummary(
        run_id=run_id,
        source_count=len(sources),
        row_count=total_rows,
        started_at=started_at,
        finished_at=finished_at,
    )
