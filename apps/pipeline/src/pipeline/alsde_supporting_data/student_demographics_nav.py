from __future__ import annotations

import argparse
import csv
import logging
import re
import time
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from pipeline.alsde_supporting_data.export_scraper_common import (
    DEFAULT_DOWNLOAD_DIR,
    HARDCODED_YEARS,
    YEAR_PATTERN,
    ExportScraperConfig,
    build_driver,
    click_export_button,
    configure_logging,
    current_year,
    get_available_years,
    navigate_to_dataset_page,
    select_year,
    wait_for_download_activity,
    wait_loading_done,
)

DATASET_SLUG = "student_demographics"
SYSTEM_FILTER_INPUT_ID = (
    "CPH_ReportCard_SupportingDataContent_gvDemographicsData_DXFREditorcol1_I"
)
DEMOGRAPHICS_GRID_LOADING_ID = (
    "CPH_ReportCard_SupportingDataContent_gvDemographicsData_LD"
)

CONFIG = ExportScraperConfig(
    link_id="SupportingData_StudentDemographics_Link",
    export_button_id="CPH_ReportCard_SupportingDataContent_btnDemographicsDataCSVExport_CD",
    dataset_slug=DATASET_SLUG,
    source_name_hint="Demographics",
    page_label="Student Demographics",
)

logger = logging.getLogger(__name__)


def slugify_system_value(system: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", system.lower()).strip("_")
    return slug or "unknown_system"


def normalize_system_for_prefix(system: str) -> str:
    return re.sub(r"[^a-z0-9]", "", system.lower())


def rename_downloaded_csv(
    downloaded_file: Path,
    year_label: str,
    prefix: str,
    download_dir: Path,
) -> Path:
    prefix_slug = slugify_system_value(prefix)
    renamed_file = download_dir / f"alsde_{DATASET_SLUG}_{year_label}_{prefix_slug}.csv"
    if renamed_file.exists() and renamed_file != downloaded_file:
        renamed_file.unlink()

    if downloaded_file != renamed_file:
        downloaded_file.replace(renamed_file)

    return renamed_file


def load_systems_for_year(download_dir: Path, year_label: str) -> list[str]:
    accountability_file = download_dir / f"alsde_accountability_{year_label}.csv"
    if not accountability_file.exists():
        logger.warning(
            "Skipping year %s: missing accountability source file %s",
            year_label,
            accountability_file,
        )
        return []

    systems: set[str] = set()
    with accountability_file.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames or "System" not in reader.fieldnames:
            logger.warning(
                "Skipping year %s: accountability file missing System column (%s)",
                year_label,
                accountability_file,
            )
            return []

        for row in reader:
            system = (row.get("System") or "").strip()
            if system:
                systems.add(system)

    values = sorted(systems)
    logger.info("Year %s: loaded %s systems from accountability", year_label, len(values))
    return values


def group_values_by_prefixes(
    normalized: Sequence[str],
    prefixes: Sequence[str],
) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for value in normalized:
        for prefix in prefixes:
            if value.startswith(prefix):
                groups[prefix].append(value)
                break
    return groups


def expand_prefix(prefix: str, values: Sequence[str]) -> list[str]:
    split_groups: dict[str, list[str]] = defaultdict(list)
    for value in values:
        next_char = value[len(prefix) : len(prefix) + 1]
        split_key = f"{prefix}{next_char}" if next_char else prefix
        split_groups[split_key].append(value)
    if len(split_groups) == 1:
        return [prefix]
    return sorted(split_groups)


def build_prefix_bins(
    systems: Sequence[str],
    target_bin_size: int,
    max_prefix_length: int,
) -> list[str]:
    normalized = sorted(
        {normalize_system_for_prefix(system) for system in systems if system}
    )
    normalized = [value for value in normalized if value]
    if not normalized:
        return []

    prefixes = sorted({value[:1] for value in normalized})
    while True:
        groups = group_values_by_prefixes(normalized, prefixes)
        next_prefixes: list[str] = []
        expanded = False
        for prefix in sorted(groups):
            values = groups[prefix]
            if len(values) <= target_bin_size or len(prefix) >= max_prefix_length:
                next_prefixes.append(prefix)
                continue
            expanded = True
            next_prefixes.extend(expand_prefix(prefix, values))

        prefixes = sorted(set(next_prefixes))
        if not expanded:
            return prefixes


def locate_system_filter_input(driver, wait: WebDriverWait):
    try:
        wait.until(ec.presence_of_element_located((By.ID, SYSTEM_FILTER_INPUT_ID)))
        elements = driver.find_elements(By.ID, SYSTEM_FILTER_INPUT_ID)
        for element in elements:
            if element.is_displayed() and element.is_enabled():
                return element
    except TimeoutException:
        logger.debug("System filter input by fixed id was not found")

    fallback_elements = driver.find_elements(
        By.CSS_SELECTOR,
        "input[id*='gvDemographicsData_DXFREditorcol1_I']",
    )
    for element in fallback_elements:
        if element.is_displayed() and element.is_enabled():
            return element

    raise TimeoutException("Could not locate System filter input for demographics grid")


def recover_demographics_page(driver, year: str) -> WebDriverWait:
    logger.warning("Recovering Student Demographics page for year %s", year)
    wait, has_year_controls = navigate_to_dataset_page(driver, CONFIG)
    if not has_year_controls:
        raise RuntimeError("Recovered page is missing year controls")
    select_year(driver, wait, year)
    logger.info("Recovered page and re-selected year %s", year)
    return wait


def apply_system_filter(
    driver,
    wait: WebDriverWait,
    system: str,
    request_wait_seconds: float,
) -> None:
    for attempt in range(3):
        try:
            try:
                wait.until(
                    ec.invisibility_of_element_located(
                        (By.ID, DEMOGRAPHICS_GRID_LOADING_ID)
                    )
                )
            except TimeoutException:
                logger.debug("Demographics grid overlay still visible before filter")

            filter_input = locate_system_filter_input(driver, wait)
            filter_input.click()
            filter_input.send_keys(Keys.CONTROL, "a")
            filter_input.send_keys(Keys.BACKSPACE)
            if system:
                filter_input.send_keys(system)
            filter_input.send_keys(Keys.ENTER)
            wait_loading_done(wait)
            try:
                wait.until(
                    ec.invisibility_of_element_located(
                        (By.ID, DEMOGRAPHICS_GRID_LOADING_ID)
                    )
                )
            except TimeoutException:
                logger.debug("Demographics grid overlay timeout after filter submit")
            if request_wait_seconds > 0:
                time.sleep(request_wait_seconds)
            return
        except (
            ElementClickInterceptedException,
            StaleElementReferenceException,
            TimeoutException,
        ):
            logger.warning(
                "System filter retry for %r",
                system,
                exc_info=logger.isEnabledFor(logging.DEBUG) or attempt == 2,
            )
            if attempt == 2:
                raise
            time.sleep(1.0)


def export_for_prefix(
    driver,
    wait: WebDriverWait,
    year: str,
    prefix: str,
    download_dir: Path,
    request_wait_seconds: float,
) -> None:
    logger.info("Exporting year %s for prefix %r", year, prefix)
    apply_system_filter(driver, wait, prefix, request_wait_seconds)
    files_before_export = {
        path.name: path.stat().st_mtime_ns for path in download_dir.glob("*.csv")
    }
    click_export_button(wait, CONFIG, year)
    expected_output_name = (
        f"alsde_{DATASET_SLUG}_{year}_{slugify_system_value(prefix)}.csv"
    )
    downloaded_file = wait_for_download_activity(
        download_dir,
        files_before_export,
        source_name_hint="Demographics",
        expected_output_name=expected_output_name,
    )
    if downloaded_file is not None:
        renamed_file = rename_downloaded_csv(downloaded_file, year, prefix, download_dir)
        logger.info(
            "Renamed downloaded CSV: %s -> %s",
            downloaded_file.name,
            renamed_file.name,
        )
    logger.info("Export request completed for year %s prefix %r", year, prefix)


def resolve_year_systems(
    year: str,
    available_years: Sequence[str],
    download_dir: Path,
    system_limit: int | None,
    prefix_target_size: int,
    max_prefix_length: int,
) -> tuple[list[str] | None, bool]:
    if not YEAR_PATTERN.fullmatch(year):
        logger.warning("Skipping malformed year value: %s", year)
        return None, True

    if year not in available_years:
        logger.warning("Skipping unknown year: %s", year)
        return None, True

    systems = load_systems_for_year(download_dir, year)
    if not systems:
        return None, True
    prefixes = build_prefix_bins(
        systems,
        target_bin_size=prefix_target_size,
        max_prefix_length=max_prefix_length,
    )
    if not prefixes:
        return None, True
    if system_limit is not None:
        prefixes = prefixes[:system_limit]
    logger.info(
        "Year %s: built %s prefix bins from %s systems",
        year,
        len(prefixes),
        len(systems),
    )
    return prefixes, False


def run(
    target_years: Sequence[str] | None,
    headless: bool,
    download_dir: Path,
    request_wait_seconds: float = 2.0,
    system_limit: int | None = None,
    prefix_target_size: int = 8,
    max_prefix_length: int = 5,
) -> None:
    download_dir.mkdir(parents=True, exist_ok=True)
    driver = build_driver(headless=headless, download_dir=download_dir)
    try:
        wait, has_year_controls = navigate_to_dataset_page(driver, CONFIG)
        if not has_year_controls:
            logger.error("Student Demographics page is missing year controls")
            return

        available_years = get_available_years(driver, wait)
        logger.info("Available years: %s", available_years)

        years_to_navigate = list(target_years) if target_years else list(HARDCODED_YEARS)
        logger.info("Years requested for export: %s", years_to_navigate)

        exported_count = 0
        skipped_count = 0
        failed_prefix_count = 0

        for year in years_to_navigate:
            prefixes, should_skip_year = resolve_year_systems(
                year,
                available_years,
                download_dir,
                system_limit,
                prefix_target_size,
                max_prefix_length,
            )
            if should_skip_year or prefixes is None:
                skipped_count += 1
                continue

            select_year(driver, wait, year)
            logger.info("Selected year now: %s", current_year(driver))

            for prefix in prefixes:
                try:
                    export_for_prefix(
                        driver,
                        wait,
                        year,
                        prefix,
                        download_dir,
                        request_wait_seconds,
                    )
                    exported_count += 1
                except (TimeoutException, StaleElementReferenceException) as exc:
                    if "Could not locate System filter input" in str(exc) or isinstance(
                        exc, StaleElementReferenceException
                    ):
                        try:
                            wait = recover_demographics_page(driver, year)
                            export_for_prefix(
                                driver,
                                wait,
                                year,
                                prefix,
                                download_dir,
                                request_wait_seconds,
                            )
                            exported_count += 1
                            continue
                        except Exception:
                            pass

                    failed_prefix_count += 1
                    logger.exception(
                        "Failed export for year %s prefix %r; continuing",
                        year,
                        prefix,
                    )
                except Exception:
                    failed_prefix_count += 1
                    logger.exception(
                        "Failed export for year %s prefix %r; continuing",
                        year,
                        prefix,
                    )

        logger.info(
            (
                "Student demographics district-loop complete "
                "(years_requested=%s, exported=%s, skipped=%s, failed_prefixes=%s)"
            ),
            len(years_to_navigate),
            exported_count,
            skipped_count,
            failed_prefix_count,
        )
    except Exception:
        logger.exception("Student demographics export run failed")
        raise
    finally:
        logger.info("Closing browser")
        driver.quit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Navigate ALSDE Student Demographics years via Selenium and export "
            "CSV data in a system/district loop."
        )
    )
    parser.add_argument(
        "--years",
        nargs="*",
        help=(
            "Optional year labels to export. Default is hardcoded years "
            "2014-2015 through 2024-2025."
        ),
    )
    parser.add_argument(
        "--download-dir",
        default=str(DEFAULT_DOWNLOAD_DIR),
        help=f"Directory for CSV downloads (default: {DEFAULT_DOWNLOAD_DIR}).",
    )
    parser.add_argument(
        "--request-wait-seconds",
        type=float,
        default=2.0,
        help="Pause between filter/export requests (default: 2.0).",
    )
    parser.add_argument(
        "--system-limit",
        type=int,
        default=None,
        help="Optional cap on prefix bins per year (debug/smoke testing).",
    )
    parser.add_argument(
        "--prefix-target-size",
        type=int,
        default=8,
        help="Target number of systems per prefix bin (default: 8).",
    )
    parser.add_argument(
        "--max-prefix-length",
        type=int,
        default=5,
        help="Maximum prefix length for splitting bins (default: 5).",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run with a visible browser window.",
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
    target_years = args.years if args.years else HARDCODED_YEARS
    run(
        target_years=target_years,
        headless=not args.headed,
        download_dir=Path(args.download_dir).resolve(),
        request_wait_seconds=args.request_wait_seconds,
        system_limit=args.system_limit,
        prefix_target_size=args.prefix_target_size,
        max_prefix_length=args.max_prefix_length,
    )


if __name__ == "__main__":
    main()
