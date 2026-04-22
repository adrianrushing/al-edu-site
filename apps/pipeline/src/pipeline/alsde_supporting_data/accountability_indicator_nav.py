from __future__ import annotations

import argparse
import logging
import re
import time
from collections.abc import Sequence
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import (
    JavascriptException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = "https://reportcard.alsde.edu"
SELECT_SCHOOL_PATH = "/SelectSchool.aspx"

MENU_LINK_CSS = ".dropdown > .nav-link"
SUPPORTING_DATA_EXPORT_LINK_XPATH = "//a[contains(text(),'Supporting Data / Export')]"
ACCOUNTABILITY_LINK_ID = "SupportingData_Accountability_Link"

YEAR_INPUT_ID = "CPH_ReportCard_SupportingDataContent_ddlReportYear_I"
YEAR_BUTTON_ID = "CPH_ReportCard_SupportingDataContent_ddlReportYear_B-1"
YEAR_LIST_TABLE_ID = "CPH_ReportCard_SupportingDataContent_ddlReportYear_DDD_L_LBT"
LOADING_PANEL_ID = "CPH_ReportCard_SupportingDataContent_lpSchools"
ACCOUNTABILITY_EXPORT_BUTTON_ID = (
    "CPH_ReportCard_SupportingDataContent_btnAccountabilityDataCSVExport_CD"
)
ACCOUNTABILITY_GRID_ID = "CPH_ReportCard_SupportingDataContent_gvAccountabilityData"
DEFAULT_DOWNLOAD_DIR = Path(__file__).resolve().parent / "downloaded"
DATASET_SLUG = "accountability"

HARDCODED_YEARS: tuple[str, ...] = (
    "2014-2015",
    "2015-2016",
    "2016-2017",
    "2017-2018",
    "2018-2019",
    "2019-2020",
    "2020-2021",
    "2021-2022",
    "2022-2023",
    "2023-2024",
    "2024-2025",
)

YEAR_PATTERN = re.compile(r"^\d{4}-\d{4}$")

logger = logging.getLogger(__name__)


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def build_driver(headless: bool, download_dir: Path) -> webdriver.Chrome:
    logger.info(
        "Creating Chrome driver (headless=%s, download_dir=%s)",
        headless,
        download_dir,
    )
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1600,1200")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": str(download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        },
    )
    return webdriver.Chrome(options=options)


def wait_loading_done(wait: WebDriverWait) -> None:
    try:
        wait.until(ec.invisibility_of_element_located((By.ID, LOADING_PANEL_ID)))
    except TimeoutException:
        logger.debug("Loading panel still visible after timeout; continuing")


def wait_for_accountability_page_ready(
    driver: webdriver.Chrome,
    timeout: int = 40,
) -> WebDriverWait:
    logger.info("Waiting for accountability controls to load")
    wait = WebDriverWait(driver, timeout)
    wait.until(ec.presence_of_element_located((By.ID, YEAR_INPUT_ID)))
    wait.until(ec.element_to_be_clickable((By.ID, YEAR_BUTTON_ID)))
    wait.until(
        lambda d: d.find_elements(By.ID, ACCOUNTABILITY_GRID_ID)
        or d.find_elements(By.ID, ACCOUNTABILITY_EXPORT_BUTTON_ID)
    )
    return wait


def navigate_to_accountability_page(
    driver: webdriver.Chrome, timeout: int = 40
) -> WebDriverWait:
    logger.info("Opening Select School page")
    driver.get(f"{BASE_URL}{SELECT_SCHOOL_PATH}")
    wait = WebDriverWait(driver, timeout)

    logger.info("Opening Menu dropdown")
    wait.until(ec.element_to_be_clickable((By.CSS_SELECTOR, MENU_LINK_CSS))).click()

    logger.info("Opening Supporting Data / Export in a new window")
    existing_handles = set(driver.window_handles)
    wait.until(
        ec.element_to_be_clickable((By.XPATH, SUPPORTING_DATA_EXPORT_LINK_XPATH))
    ).click()
    wait.until(lambda d: len(set(d.window_handles) - existing_handles) == 1)

    new_handles = set(driver.window_handles) - existing_handles
    new_handle = next(iter(new_handles))
    driver.switch_to.window(new_handle)
    logger.info("Switched to supporting data window")

    wait.until(ec.element_to_be_clickable((By.ID, ACCOUNTABILITY_LINK_ID))).click()
    logger.info("Opened Accountability Indicators page")

    wait = wait_for_accountability_page_ready(driver, timeout=timeout)
    wait_loading_done(wait)
    return wait


def parse_years_from_page_html(page_html: str) -> list[str]:
    soup = BeautifulSoup(page_html, "html.parser")
    table = soup.select_one(f"table#{YEAR_LIST_TABLE_ID}")
    if table is None:
        return []

    years = {
        text
        for row in table.select("tr")
        if (text := row.get_text(" ", strip=True)) and YEAR_PATTERN.fullmatch(text)
    }
    return sorted(years, reverse=True)


def is_year_dropdown_open(driver: webdriver.Chrome) -> bool:
    table = driver.find_elements(By.ID, YEAR_LIST_TABLE_ID)
    if table and table[0].is_displayed():
        return True

    options = driver.find_elements(
        By.XPATH,
        f"//table[@id='{YEAR_LIST_TABLE_ID}']//td[contains(@id,'ddlReportYear_DDD_L_LBI')]",
    )
    return any(option.is_displayed() for option in options)


def wait_for_year_rows_visible(wait: WebDriverWait) -> None:
    wait.until(
        lambda d: [
            option
            for option in d.find_elements(
                By.XPATH,
                f"//table[@id='{YEAR_LIST_TABLE_ID}']//td[contains(@id,'ddlReportYear_DDD_L_LBI')]",
            )
            if option.is_displayed()
        ]
    )


def ensure_year_dropdown_open(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    if is_year_dropdown_open(driver):
        wait_for_year_rows_visible(wait)
        return

    wait.until(ec.element_to_be_clickable((By.ID, YEAR_BUTTON_ID))).click()
    wait.until(ec.presence_of_element_located((By.ID, YEAR_LIST_TABLE_ID)))
    wait.until(lambda d: is_year_dropdown_open(d))
    wait_for_year_rows_visible(wait)


def get_available_years(driver: webdriver.Chrome, wait: WebDriverWait) -> list[str]:
    logger.info("Opening year selector and parsing available years")
    ensure_year_dropdown_open(driver, wait)
    years = parse_years_from_page_html(driver.page_source)
    if years:
        return years
    raise RuntimeError("Could not parse reporting years from year table HTML")


def select_year_via_devexpress_js(driver: webdriver.Chrome, year_label: str) -> bool:
    script = """
        const target = arguments[0];
        const combo = window.ddlReportYear;
        if (!combo || typeof combo.GetItemCount !== 'function') {
            return false;
        }
        const count = combo.GetItemCount();
        for (let i = 0; i < count; i += 1) {
            const item = combo.GetItem(i);
            if (!item || !item.text) {
                continue;
            }
            if (item.text.trim() !== target) {
                continue;
            }
            if (typeof combo.SetSelectedIndex === 'function') {
                combo.SetSelectedIndex(i);
            }
            if (typeof combo.SetText === 'function') {
                combo.SetText(target);
            }
            if (typeof combo.HideDropDown === 'function') {
                combo.HideDropDown();
            }
            return true;
        }
        return false;
    """
    try:
        result = driver.execute_script(script, year_label)
    except JavascriptException:
        logger.warning("DevExpress fallback raised JavascriptException", exc_info=True)
        return False

    return bool(result)


def select_year(driver: webdriver.Chrome, wait: WebDriverWait, year_label: str) -> None:
    for attempt in range(3):
        try:
            logger.info("Selecting year '%s' (attempt %s/3)", year_label, attempt + 1)
            ensure_year_dropdown_open(driver, wait)

            option_xpath = (
                f"//table[@id='{YEAR_LIST_TABLE_ID}']"
                "//td[contains(@id,'ddlReportYear_DDD_L_LBI') and "
                f"normalize-space()='{year_label}']"
            )
            used_fallback = False
            try:
                wait.until(ec.element_to_be_clickable((By.XPATH, option_xpath))).click()
            except (TimeoutException, StaleElementReferenceException):
                logger.warning(
                    "Selenium click failed for year '%s'; trying DevExpress fallback",
                    year_label,
                    exc_info=True,
                )
                used_fallback = True
                if not select_year_via_devexpress_js(driver, year_label):
                    raise

            wait.until(
                lambda d: d.find_element(By.ID, YEAR_INPUT_ID)
                .get_attribute("value")
                .strip()
                == year_label
            )
            wait_loading_done(wait)
            wait.until(
                lambda d: d.find_elements(By.ID, ACCOUNTABILITY_GRID_ID)
                or d.find_elements(By.ID, ACCOUNTABILITY_EXPORT_BUTTON_ID)
            )
            if used_fallback:
                logger.info("Year '%s' selected with DevExpress fallback", year_label)
            else:
                logger.info(
                    "Successfully selected year '%s' via Selenium click", year_label
                )
            return
        except (StaleElementReferenceException, TimeoutException):
            logger.warning("Year selection retry for '%s'", year_label, exc_info=True)
            if attempt == 2:
                raise
            time.sleep(1.0)


def current_year(driver: webdriver.Chrome) -> str:
    return driver.find_element(By.ID, YEAR_INPUT_ID).get_attribute("value").strip()


def click_export_button(wait: WebDriverWait, year_label: str) -> None:
    logger.info("Requesting CSV export for year '%s'", year_label)
    wait.until(
        ec.element_to_be_clickable((By.ID, ACCOUNTABILITY_EXPORT_BUTTON_ID))
    ).click()
    wait_loading_done(wait)


def wait_for_download_activity(
    download_dir: Path,
    before_files: dict[str, int],
    source_name_hint: str,
    expected_output_name: str,
) -> Path | None:
    timeout_seconds = 30
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        current_csv_files = list(download_dir.glob("*.csv"))
        changed_csv_files = [
            path
            for path in current_csv_files
            if path.name not in before_files
            or path.stat().st_mtime_ns != before_files[path.name]
        ]
        if changed_csv_files:
            matching_files = [
                path
                for path in changed_csv_files
                if source_name_hint.lower() in path.name.lower()
                or path.name == expected_output_name
            ]
            if matching_files:
                return max(matching_files, key=lambda path: path.stat().st_mtime_ns)

        if any(path.suffix == ".crdownload" for path in download_dir.glob("*")):
            time.sleep(0.5)
            continue
        time.sleep(0.5)

    logger.warning(
        "No new download artifact observed within %s seconds; continuing",
        timeout_seconds,
    )
    return None


def rename_downloaded_csv(
    downloaded_file: Path, year_label: str, download_dir: Path
) -> Path:
    renamed_file = download_dir / f"alsde_{DATASET_SLUG}_{year_label}.csv"
    if renamed_file.exists() and renamed_file != downloaded_file:
        renamed_file.unlink()

    if downloaded_file != renamed_file:
        downloaded_file.replace(renamed_file)

    return renamed_file


def run(target_years: Sequence[str] | None, headless: bool, download_dir: Path) -> None:
    download_dir.mkdir(parents=True, exist_ok=True)
    driver = build_driver(headless=headless, download_dir=download_dir)
    try:
        wait = navigate_to_accountability_page(driver)
        available_years = get_available_years(driver, wait)
        logger.info("Available years: %s", available_years)

        years_to_navigate = list(target_years) if target_years else list(HARDCODED_YEARS)
        logger.info("Years requested for export: %s", years_to_navigate)

        exported_count = 0
        skipped_count = 0
        for year in years_to_navigate:
            if not YEAR_PATTERN.fullmatch(year):
                logger.warning("Skipping malformed year value: %s", year)
                skipped_count += 1
                continue

            if year not in available_years:
                logger.warning("Skipping unknown year: %s", year)
                skipped_count += 1
                continue

            select_year(driver, wait, year)
            logger.info("Selected year now: %s", current_year(driver))
            files_before_export = {
                path.name: path.stat().st_mtime_ns for path in download_dir.glob("*.csv")
            }
            click_export_button(wait, year)
            expected_output_name = f"alsde_{DATASET_SLUG}_{year}.csv"
            downloaded_file = wait_for_download_activity(
                download_dir,
                files_before_export,
                source_name_hint="Accountability",
                expected_output_name=expected_output_name,
            )
            if downloaded_file is not None:
                renamed_file = rename_downloaded_csv(downloaded_file, year, download_dir)
                logger.info(
                    "Renamed downloaded CSV: %s -> %s",
                    downloaded_file.name,
                    renamed_file.name,
                )
            exported_count += 1
            logger.info("Export request completed for year '%s'", year)

        logger.info(
            "Accountability exports complete (requested=%s, exported=%s, skipped=%s)",
            len(years_to_navigate),
            exported_count,
            skipped_count,
        )
    except Exception:
        logger.exception("Accountability export run failed")
        raise
    finally:
        logger.info("Closing browser")
        driver.quit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Navigate ALSDE Accountability Indicators years via Selenium and export "
            "CSV data for each requested year."
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
    )


if __name__ == "__main__":
    main()
