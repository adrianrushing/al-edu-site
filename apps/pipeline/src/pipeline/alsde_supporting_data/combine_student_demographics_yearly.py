from __future__ import annotations

import argparse
import csv
import logging
import re
from pathlib import Path

from pipeline.alsde_supporting_data.export_scraper_common import (
    DEFAULT_DOWNLOAD_DIR,
    HARDCODED_YEARS,
)

DATASET_PREFIX = "alsde_student_demographics_"
YEAR_RE = re.compile(r"^(\d{4}-\d{4})$")
PREFIX_SUFFIX_RE = re.compile(r"^[a-z]{1,5}$")

logger = logging.getLogger(__name__)


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def parse_demographics_name(path: Path) -> tuple[str, str | None] | None:
    stem = path.stem
    if not stem.startswith(DATASET_PREFIX):
        return None

    remainder = stem.removeprefix(DATASET_PREFIX)
    year, sep, suffix = remainder.partition("_")
    if not YEAR_RE.fullmatch(year):
        return None
    if not sep:
        return year, None
    return year, suffix


def choose_input_files(files: list[Path]) -> list[Path]:
    prefix_files = []
    fallback_files = []
    for file_path in files:
        parsed = parse_demographics_name(file_path)
        if parsed is None:
            continue
        _, suffix = parsed
        if not suffix:
            continue
        fallback_files.append(file_path)
        if PREFIX_SUFFIX_RE.fullmatch(suffix):
            prefix_files.append(file_path)

    selected = prefix_files if prefix_files else fallback_files
    return sorted(selected)


def row_count(file_path: Path) -> int:
    with file_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def build_source_groups(download_dir: Path, year: str) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}

    alsde_files = [
        path
        for path in download_dir.glob(f"{DATASET_PREFIX}{year}*.csv")
        if path.is_file()
    ]
    parsed_inputs = choose_input_files(alsde_files)
    prefix_inputs = [
        path
        for path in parsed_inputs
        if (parsed := parse_demographics_name(path))
        and parsed[1]
        and PREFIX_SUFFIX_RE.fullmatch(parsed[1])
    ]
    if prefix_inputs:
        groups["prefix_bins"] = sorted(prefix_inputs)
    if parsed_inputs:
        groups["renamed_suffix"] = sorted(parsed_inputs)

    end_year = year.split("-")[1]
    raw_exports = sorted(
        path
        for path in download_dir.glob(
            f"SupportingData_StudentDemographics_{end_year}_*.csv"
        )
        if path.is_file()
    )
    if raw_exports:
        groups["raw_exports"] = raw_exports

    yearly_file = download_dir / f"{DATASET_PREFIX}{year}.csv"
    if yearly_file.exists() and yearly_file.is_file():
        groups["existing_yearly"] = [yearly_file]

    return groups


def choose_best_source_group(
    source_groups: dict[str, list[Path]],
) -> tuple[str, list[Path], int] | None:
    ranked: list[tuple[str, list[Path], int]] = []
    for label, files in source_groups.items():
        total_rows = 0
        for file_path in files:
            try:
                total_rows += row_count(file_path)
            except Exception:
                logger.warning("Could not count rows for %s", file_path)
        ranked.append((label, files, total_rows))

    ranked.sort(
        key=lambda item: (
            item[2],
            1 if item[0] == "raw_exports" else 0,
            1 if item[0] == "renamed_suffix" else 0,
            1 if item[0] == "prefix_bins" else 0,
            1 if item[0] == "existing_yearly" else 0,
        ),
        reverse=True,
    )
    if not ranked:
        return None
    return ranked[0]


def combine_year_files(download_dir: Path, year: str) -> bool:
    source_groups = build_source_groups(download_dir, year)
    best = choose_best_source_group(source_groups)
    if best is None:
        logger.warning("No student demographics source files found for year %s", year)
        return False
    source_label, selected_files, source_rows = best
    if source_rows <= 0:
        logger.warning(
            "Best source for year %s has no rows (%s); skipping combine",
            year,
            source_label,
        )
        return False

    output_path = download_dir / f"{DATASET_PREFIX}{year}.csv"
    selected_files = [
        file_path for file_path in selected_files if file_path != output_path
    ]
    if not selected_files:
        logger.info(
            "Year %s already has best available yearly file; no rewrite needed", year
        )
        return True

    temp_path = output_path.with_suffix(".csv.tmp")

    total_rows = 0
    fieldnames: list[str] | None = None
    with temp_path.open("w", newline="", encoding="utf-8") as out_handle:
        writer: csv.DictWriter[str] | None = None
        for input_file in selected_files:
            with input_file.open(newline="", encoding="utf-8-sig") as in_handle:
                reader = csv.DictReader(in_handle)
                if not reader.fieldnames:
                    logger.warning("Skipping empty CSV: %s", input_file)
                    continue

                if fieldnames is None:
                    fieldnames = list(reader.fieldnames)
                    writer = csv.DictWriter(out_handle, fieldnames=fieldnames)
                    writer.writeheader()
                elif list(reader.fieldnames) != fieldnames:
                    logger.warning(
                        "Skipping mismatched header file %s",
                        input_file,
                    )
                    continue

                assert writer is not None
                for row in reader:
                    writer.writerow(row)
                    total_rows += 1

    if fieldnames is None:
        temp_path.unlink(missing_ok=True)
        logger.warning("No readable rows found for year %s", year)
        return False

    temp_path.replace(output_path)
    logger.info(
        "Combined %s files into %s (%s rows)",
        len(selected_files),
        output_path.name,
        total_rows,
    )
    logger.info("Used source group %s for year %s", source_label, year)
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Combine student demographics partition files into yearly CSV files."
    )
    parser.add_argument(
        "--years",
        nargs="*",
        help="Optional years to combine (default: 2015-2016 through 2024-2025).",
    )
    parser.add_argument(
        "--download-dir",
        default=str(DEFAULT_DOWNLOAD_DIR),
        help=f"Download directory (default: {DEFAULT_DOWNLOAD_DIR}).",
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
    download_dir = Path(args.download_dir).resolve()
    years = (
        args.years
        if args.years
        else [year for year in HARDCODED_YEARS if year != "2014-2015"]
    )

    combined = 0
    skipped = 0
    for year in years:
        if combine_year_files(download_dir, year):
            combined += 1
        else:
            skipped += 1

    logger.info(
        "Student demographics combine complete (combined=%s, skipped=%s)",
        combined,
        skipped,
    )


if __name__ == "__main__":
    main()
