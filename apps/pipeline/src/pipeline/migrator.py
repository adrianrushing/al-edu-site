from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from psycopg import Connection
from psycopg.rows import dict_row


@dataclass(frozen=True)
class Migration:
    name: str
    path: Path
    checksum: str


def migration_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def discover_migrations(migrations_dir: Path) -> list[Migration]:
    sql_paths = sorted(migrations_dir.glob("*.sql"))
    return [
        Migration(name=path.name, path=path, checksum=migration_checksum(path))
        for path in sql_paths
    ]


def ensure_migration_table(conn: Connection) -> None:
    ddl = """
    CREATE SCHEMA IF NOT EXISTS pipeline_meta;

    CREATE TABLE IF NOT EXISTS pipeline_meta.schema_migrations (
        migration_name TEXT PRIMARY KEY,
        checksum TEXT NOT NULL,
        applied_at TIMESTAMPTZ NOT NULL,
        execution_ms INTEGER NOT NULL
    );
    """
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def load_applied_migrations(conn: Connection) -> dict[str, dict[str, object]]:
    query = """
    SELECT migration_name, checksum, applied_at, execution_ms
    FROM pipeline_meta.schema_migrations
    ORDER BY migration_name
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query)
        rows = cur.fetchall()
    return {str(row["migration_name"]): dict(row) for row in rows}


def plan_migrations(
    conn: Connection, migrations_dir: Path
) -> list[tuple[Migration, str]]:
    ensure_migration_table(conn)
    applied = load_applied_migrations(conn)
    plan: list[tuple[Migration, str]] = []

    for migration in discover_migrations(migrations_dir):
        existing = applied.get(migration.name)
        if existing is None:
            plan.append((migration, "pending"))
            continue

        existing_checksum = str(existing["checksum"])
        if existing_checksum != migration.checksum:
            plan.append((migration, "drifted"))
            continue

        plan.append((migration, "applied"))

    return plan


def apply_migrations(
    conn: Connection, migrations_dir: Path, dry_run: bool = False
) -> list[str]:
    messages: list[str] = []
    plan = plan_migrations(conn, migrations_dir)

    drifted = [m.name for m, status in plan if status == "drifted"]
    if drifted:
        raise RuntimeError("Migration checksum drift detected for: " + ", ".join(drifted))

    pending = [migration for migration, status in plan if status == "pending"]
    if not pending:
        messages.append("No pending migrations.")
        return messages

    for migration in pending:
        sql_text = migration.path.read_text(encoding="utf-8")
        if dry_run:
            messages.append(f"DRY RUN - would apply {migration.name}")
            continue

        start = datetime.now(tz=UTC)
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(sql_text)
                cur.execute(
                    """
                    INSERT INTO pipeline_meta.schema_migrations
                    (migration_name, checksum, applied_at, execution_ms)
                    VALUES (%s, %s, now(), %s)
                    """,
                    (
                        migration.name,
                        migration.checksum,
                        int((datetime.now(tz=UTC) - start).total_seconds() * 1000),
                    ),
                )

        messages.append(f"Applied {migration.name}")

    return messages
