from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from pipeline.alsde_supporting_data.export_scraper_common import (
    DEFAULT_DOWNLOAD_DIR,
    HARDCODED_YEARS,
)

DATASET_PATTERNS = {
    "school_accountability": "alsde_accountability_*.csv",
    "student_demographics": "alsde_student_demographics_*.csv",
    "teacher_demographics": "alsde_educator_demographics_*.csv",
    "teacher_experience": "alsde_educator_experience_*.csv",
}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ManifestRow:
    dataset_type: str
    year_label: str
    path: str
    size_bytes: int
    modified_at_epoch: float
    row_count: int
    header_signature: str


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def parse_year_from_name(path: Path, prefix: str) -> str | None:
    stem = path.stem
    if not stem.startswith(prefix):
        return None
    year = stem.removeprefix(prefix)
    if len(year) == 9 and year[4] == "-":
        return year
    return None


def inspect_csv(path: Path) -> tuple[int, str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        header_sig = hashlib.sha1(
            ",".join(header).encode("utf-8"), usedforsecurity=False
        ).hexdigest()
        row_count = sum(1 for _ in reader)
    return row_count, header_sig


def build_manifest(source_dir: Path) -> list[ManifestRow]:
    manifest: list[ManifestRow] = []
    prefix_map = {
        "school_accountability": "alsde_accountability_",
        "student_demographics": "alsde_student_demographics_",
        "teacher_demographics": "alsde_educator_demographics_",
        "teacher_experience": "alsde_educator_experience_",
    }

    for dataset, pattern in DATASET_PATTERNS.items():
        for file_path in sorted(source_dir.glob(pattern)):
            if not file_path.is_file():
                continue

            year = parse_year_from_name(file_path, prefix_map[dataset])
            if year is None:
                continue

            row_count, header_signature = inspect_csv(file_path)
            stat = file_path.stat()
            manifest.append(
                ManifestRow(
                    dataset_type=dataset,
                    year_label=year,
                    path=str(file_path),
                    size_bytes=stat.st_size,
                    modified_at_epoch=stat.st_mtime,
                    row_count=row_count,
                    header_signature=header_signature,
                )
            )

    return manifest


def validate_required_years(manifest: list[ManifestRow]) -> bool:
    required_years = [year for year in HARDCODED_YEARS if year != "2014-2015"]
    ok = True
    grouped: dict[str, set[str]] = {}
    for row in manifest:
        grouped.setdefault(row.dataset_type, set()).add(row.year_label)

    for dataset in DATASET_PATTERNS:
        present = grouped.get(dataset, set())
        missing = [year for year in required_years if year not in present]
        if missing:
            ok = False
            logger.error("Missing canonical files for %s: %s", dataset, missing)
        else:
            logger.info("%s has all required years (%s)", dataset, len(required_years))

    return ok


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build and validate canonical staging-ingest manifest for ALSDE files."
        )
    )
    parser.add_argument(
        "--source-dir",
        default=str(DEFAULT_DOWNLOAD_DIR),
        help=f"Directory containing ALSDE downloads (default: {DEFAULT_DOWNLOAD_DIR})",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Optional path to write full manifest as JSON.",
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

    manifest = build_manifest(source_dir)
    if not manifest:
        raise RuntimeError(f"No canonical ALSDE files found in {source_dir}")

    for row in manifest:
        logger.info(
            "manifest dataset=%s year=%s rows=%s file=%s",
            row.dataset_type,
            row.year_label,
            row.row_count,
            Path(row.path).name,
        )

    if args.output_json:
        output_path = Path(args.output_json).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps([asdict(row) for row in manifest], indent=2),
            encoding="utf-8",
        )
        logger.info("Wrote manifest JSON: %s", output_path)

    if not validate_required_years(manifest):
        raise RuntimeError("Manifest validation failed: missing canonical year files")

    logger.info("Manifest validation passed")


if __name__ == "__main__":
    main()
