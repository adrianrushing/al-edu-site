from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.db import connect
from pipeline.manifest import load_manifest
from pipeline.migrator import apply_migrations, discover_migrations, plan_migrations


def default_migrations_dir() -> Path:
    return Path(__file__).resolve().parent / "sql" / "migrations"


def cmd_status(migrations_dir: Path) -> int:
    with connect() as conn:
        rows = plan_migrations(conn, migrations_dir)

    for migration, status in rows:
        print(f"{status:8}  {migration.name}")
    return 0


def cmd_plan(migrations_dir: Path) -> int:
    return cmd_status(migrations_dir)


def cmd_apply(migrations_dir: Path, dry_run: bool) -> int:
    if dry_run:
        for migration in discover_migrations(migrations_dir):
            print(f"DRY RUN - would apply {migration.name}")
        return 0

    with connect() as conn:
        messages = apply_migrations(conn, migrations_dir, dry_run=dry_run)

    for message in messages:
        print(message)
    return 0


def cmd_manifest() -> int:
    manifest = load_manifest()
    print(f"manifest_version={manifest.version}")
    print(f"steps={len(manifest.steps)}")
    for step in manifest.steps:
        step_name = step.get("name", "unnamed_step")
        layer = step.get("target_layer", "unknown")
        print(f"- {step_name} -> {layer}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="EFLT medallion schema migration runner"
    )
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=default_migrations_dir(),
        help="Path to SQL migration files",
    )

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Show applied/pending migration status")
    sub.add_parser("plan", help="Alias for status")

    apply_parser = sub.add_parser("apply", help="Apply pending migrations")
    apply_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print migrations that would run without executing SQL",
    )

    sub.add_parser("manifest", help="Print ETL step manifest summary")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    migrations_dir: Path = args.migrations_dir

    if args.command == "status":
        return cmd_status(migrations_dir)
    if args.command == "plan":
        return cmd_plan(migrations_dir)
    if args.command == "apply":
        return cmd_apply(migrations_dir, dry_run=bool(args.dry_run))
    if args.command == "manifest":
        return cmd_manifest()
    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
