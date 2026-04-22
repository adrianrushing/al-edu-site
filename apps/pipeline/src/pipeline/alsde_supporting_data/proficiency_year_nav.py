from __future__ import annotations

import argparse
import logging
import re
import time
from collections.abc import Sequence

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

URL = "https://reportcard.alsde.edu/SupportingData_Proficiency.aspx"

YEAR_INPUT_ID = "CPH_ReportCard_SupportingDataContent_ddlReportYear_I"
YEAR_BUTTON_ID = "CPH_ReportCard_SupportingDataContent_ddlReportYear_B-1"
YEAR_LIST_TABLE_ID = "CPH_ReportCard_SupportingDataContent_ddlReportYear_DDD_L_LBT"
LOADING_PANEL_ID = "CPH_ReportCard_SupportingDataContent_lpSchools"
GRID_ID = "CPH_ReportCard_SupportingDataContent_gvProficiencyData"

logger = logging.getLogger(__name__)


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def build_driver(headless: bool) -> webdriver.Chrome:
    logger.info("Creating Chrome driver (headless=%s)", headless)
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1600,1200")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    return webdriver.Chrome(options=options)


def wait_for_page_ready(driver: webdriver.Chrome, timeout: int = 40) -> WebDriverWait:
    logger.info("Waiting for proficiency page controls to load")
    wait = WebDriverWait(driver, timeout)
    wait.until(ec.presence_of_element_located((By.ID, YEAR_INPUT_ID)))
    wait.until(ec.element_to_be_clickable((By.ID, YEAR_BUTTON_ID)))
    wait.until(ec.presence_of_element_located((By.ID, GRID_ID)))
    return wait


def wait_loading_done(wait: WebDriverWait) -> None:
    try:
        wait.until(ec.invisibility_of_element_located((By.ID, LOADING_PANEL_ID)))
    except TimeoutException:
        logger.debug("Loading panel still visible after timeout; continuing")
        return


def open_year_dropdown(wait: WebDriverWait) -> None:
    wait.until(ec.element_to_be_clickable((By.ID, YEAR_BUTTON_ID))).click()
    wait.until(ec.presence_of_element_located((By.ID, YEAR_LIST_TABLE_ID)))


def parse_years_from_page_html(page_html: str) -> list[str]:
    soup = BeautifulSoup(page_html, "html.parser")

    rows = soup.select(f"table#{YEAR_LIST_TABLE_ID} tr[id*='ddlReportYear_DDD_L_LBI']")
    years = []
    for row in rows:
        text = row.get_text(" ", strip=True)
        if text:
            years.append(text)

    if years:
        return sorted(set(years), reverse=True)

    script_text = "\n".join(script.get_text() for script in soup.find_all("script"))
    return sorted(set(re.findall(r"'text':'([^']+)'", script_text)), reverse=True)


def get_available_years(driver: webdriver.Chrome, wait: WebDriverWait) -> list[str]:
    logger.info("Opening year selector and parsing available years")
    open_year_dropdown(wait)
    years = parse_years_from_page_html(driver.page_source)

    if years:
        return years

    raise RuntimeError("Could not parse reporting years from page HTML")


def select_year(driver: webdriver.Chrome, wait: WebDriverWait, year_label: str) -> None:
    for attempt in range(3):
        try:
            logger.info("Selecting year '%s' (attempt %s/3)", year_label, attempt + 1)
            open_year_dropdown(wait)

            option_xpath = (
                "//tr[contains(@id,'ddlReportYear_DDD_L_LBI')]"
                f"/td[normalize-space()='{year_label}']"
            )
            wait.until(ec.element_to_be_clickable((By.XPATH, option_xpath))).click()

            wait.until(
                lambda d: d.find_element(By.ID, YEAR_INPUT_ID)
                .get_attribute("value")
                .strip()
                == year_label
            )
            wait_loading_done(wait)
            wait.until(ec.presence_of_element_located((By.ID, GRID_ID)))
            logger.info("Successfully selected year '%s'", year_label)
            return
        except (StaleElementReferenceException, TimeoutException):
            logger.warning("Year selection retry for '%s'", year_label, exc_info=True)
            if attempt == 2:
                raise
            time.sleep(1.0)


def current_year(driver: webdriver.Chrome) -> str:
    return driver.find_element(By.ID, YEAR_INPUT_ID).get_attribute("value").strip()


def run(target_years: Sequence[str] | None, headless: bool) -> None:
    driver = build_driver(headless=headless)
    try:
        logger.info("Navigating to %s", URL)
        driver.get(URL)
        wait = wait_for_page_ready(driver)
        wait_loading_done(wait)

        available_years = get_available_years(driver, wait)
        logger.info("Available years: %s", available_years)

        years_to_navigate = list(target_years) if target_years else available_years
        logger.info("Years requested for navigation: %s", years_to_navigate)
        for year in years_to_navigate:
            if year not in available_years:
                logger.warning("Skipping unknown year: %s", year)
                continue

            select_year(driver, wait, year)
            logger.info("Selected year now: %s", current_year(driver))

        logger.info("Pilot year navigation complete")
    except Exception:
        logger.exception("Pilot year navigation failed")
        raise
    finally:
        logger.info("Closing browser")
        driver.quit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Navigate ALSDE proficiency years using Selenium and parse year options "
            "from page HTML with BeautifulSoup."
        )
    )
    parser.add_argument(
        "--years",
        nargs="*",
        default=["2020-2021"],
        help="Optional year labels to navigate (default: 2020-2021).",
    )
    parser.add_argument(
        "--all-years",
        action="store_true",
        help="Ignore --years and navigate all years found in the selector.",
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
    target_years = None if args.all_years else args.years
    run(target_years=target_years, headless=not args.headed)


if __name__ == "__main__":
    main()
