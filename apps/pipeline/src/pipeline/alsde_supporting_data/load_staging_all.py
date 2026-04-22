from __future__ import annotations

import argparse
import logging
from pathlib import Path

import psycopg

from pipeline.alsde_supporting_data import combine_student_demographics_yearly
from pipeline.alsde_supporting_data.build_staging_ingest_manifest import (
    build_manifest,
    validate_required_years,
)
from pipeline.alsde_supporting_data.load_accountability_remote import (
    _load_remote_database_url,
    _with_keepalive_params,
)
from pipeline.alsde_supporting_data.load_accountability_remote import (
    run_load as run_accountability_load,
)
from pipeline.alsde_supporting_data.load_student_demographics_remote import (
    run_load as run_student_demographics_load,
)
from pipeline.alsde_supporting_data.load_teacher_demographics_remote import (
    run_load as run_teacher_demographics_load,
)
from pipeline.alsde_supporting_data.load_teacher_experience_remote import (
    run_load as run_teacher_experience_load,
)

DATASETS = (
    "school_accountability",
    "student_demographics",
    "teacher_demographics",
    "teacher_experience",
)

TABLE_BY_DATASET = {
    "school_accountability": "staging.stg_school_accountability",
    "student_demographics": "staging.stg_student_demographics",
    "teacher_demographics": "staging.stg_teacher_demographics",
    "teacher_experience": "staging.stg_teacher_experience",
}

KEY_COLUMNS = {
    "school_accountability": (
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
    ),
    "student_demographics": (
        "year",
        "system",
        "school",
        "grade",
        "gender",
        "ethnicity",
        "sub_population",
        "total_student_count",
        "asian",
        "black_or_african_american",
        "american_indian_alaska_native",
        "native_hawaiian_pacific_islander",
        "white",
        "two_or_more_races",
    ),
    "teacher_demographics": (
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
    ),
    "teacher_experience": (
        "year",
        "system",
        "school",
        "gender",
        "race",
        "ethnicity",
        "sub_population",
        "total_count",
        "experienced_count",
        "experienced_rate",
        "inexperienced_count",
        "inexperienced_rate",
    ),
}

logger = logging.getLogger(__name__)


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def parse_datasets(raw_values: list[str] | None) -> tuple[str, ...]:
    if not raw_values:
        return DATASETS
    selected = []
    for value in raw_values:
        if value not in DATASETS:
            raise RuntimeError(f"Unknown dataset: {value}")
        selected.append(value)
    return tuple(selected)


def preflight_connection(database_url: str) -> None:
    with psycopg.connect(database_url, connect_timeout=15) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_user, current_database()")
            user, db = cur.fetchone()
            logger.info("connected user=%s db=%s", user, db)


def run_manifest_phase(source_dir: Path) -> None:
    manifest = build_manifest(source_dir)
    if not manifest:
        raise RuntimeError("No canonical files found")
    if not validate_required_years(manifest):
        raise RuntimeError("Manifest validation failed")
    logger.info("manifest phase passed rows=%s", len(manifest))


def run_combine_phase(source_dir: Path) -> None:
    years = [
        year
        for year in combine_student_demographics_yearly.HARDCODED_YEARS
        if year != "2014-2015"
    ]
    combined = 0
    for year in years:
        if combine_student_demographics_yearly.combine_year_files(source_dir, year):
            combined += 1
    logger.info("combine phase completed combined_years=%s", combined)


def table_count(conn: psycopg.Connection, table_name: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        return int(cur.fetchone()[0])


def duplicate_group_count(
    conn: psycopg.Connection,
    table_name: str,
    key_columns: tuple[str, ...],
) -> int:
    keys = ", ".join(key_columns)
    sql = f"""
        SELECT COUNT(*)
        FROM (
            SELECT {keys}, COUNT(*) AS c
            FROM {table_name}
            GROUP BY {keys}
            HAVING COUNT(*) > 1
        ) dup
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return int(cur.fetchone()[0])


def year_coverage(conn: psycopg.Connection, table_name: str) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT DISTINCT year FROM {table_name} WHERE year IS NOT NULL ORDER BY year"
        )
        return [str(row[0]) for row in cur.fetchall()]


def run_load_for_dataset(
    dataset: str,
    source_dir: Path,
    database_url: str,
    batch_size: int,
) -> None:
    if dataset == "school_accountability":
        run_accountability_load(
            source_dir=source_dir,
            file_pattern="alsde_accountability_*.csv",
            database_url=database_url,
            batch_size=batch_size,
        )
    elif dataset == "student_demographics":
        run_student_demographics_load(
            source_dir=source_dir,
            database_url=database_url,
            batch_size=batch_size,
        )
    elif dataset == "teacher_demographics":
        run_teacher_demographics_load(
            source_dir=source_dir,
            database_url=database_url,
            batch_size=batch_size,
        )
    elif dataset == "teacher_experience":
        run_teacher_experience_load(
            source_dir=source_dir,
            database_url=database_url,
            batch_size=batch_size,
        )
    else:
        raise RuntimeError(f"Unsupported dataset {dataset}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Single phased loader for existing ALSDE staging tables."
    )
    parser.add_argument(
        "--source-dir",
        default=str(combine_student_demographics_yearly.DEFAULT_DOWNLOAD_DIR),
        help="Directory containing canonical ALSDE files.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Remote PostgreSQL URL.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20_000,
        help="Rows per chunk for loaders.",
    )
    parser.add_argument(
        "--datasets",
        nargs="*",
        default=None,
        help=(
            "Optional subset from: school_accountability student_demographics "
            "teacher_demographics teacher_experience"
        ),
    )
    parser.add_argument(
        "--skip-manifest",
        action="store_true",
        help="Skip manifest validation phase.",
    )
    parser.add_argument(
        "--skip-combine",
        action="store_true",
        help="Skip student demographics combine phase.",
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

    selected_datasets = parse_datasets(args.datasets)
    raw_url = _load_remote_database_url(args.database_url)
    database_url = _with_keepalive_params(raw_url)

    logger.info("phase=preflight")
    preflight_connection(database_url)

    if not args.skip_manifest:
        logger.info("phase=manifest")
        run_manifest_phase(source_dir)

    if "student_demographics" in selected_datasets and not args.skip_combine:
        logger.info("phase=combine")
        run_combine_phase(source_dir)

    before_counts: dict[str, int] = {}
    with psycopg.connect(database_url, connect_timeout=15) as conn:
        for dataset in selected_datasets:
            before_counts[dataset] = table_count(conn, TABLE_BY_DATASET[dataset])

    failures: list[str] = []
    for dataset in selected_datasets:
        logger.info("phase=load dataset=%s", dataset)
        try:
            run_load_for_dataset(
                dataset=dataset,
                source_dir=source_dir,
                database_url=database_url,
                batch_size=args.batch_size,
            )
        except Exception:
            failures.append(dataset)
            logger.exception("dataset load failed: %s", dataset)

    logger.info("phase=qa")
    with psycopg.connect(database_url, connect_timeout=15) as conn:
        for dataset in selected_datasets:
            table_name = TABLE_BY_DATASET[dataset]
            after = table_count(conn, table_name)
            before = before_counts.get(dataset, 0)
            years = year_coverage(conn, table_name)
            dup_groups = duplicate_group_count(conn, table_name, KEY_COLUMNS[dataset])
            logger.info(
                (
                    "qa dataset=%s table=%s before=%s after=%s "
                    "delta=%s dup_groups=%s years=%s"
                ),
                dataset,
                table_name,
                before,
                after,
                after - before,
                dup_groups,
                years,
            )

    if failures:
        raise SystemExit(f"staging load completed with failures: {failures}")

    logger.info("staging load completed successfully datasets=%s", selected_datasets)


if __name__ == "__main__":
    main()
