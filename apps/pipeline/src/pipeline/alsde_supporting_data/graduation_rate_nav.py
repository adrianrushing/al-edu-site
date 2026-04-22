from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.alsde_supporting_data.export_scraper_common import (
    DEFAULT_DOWNLOAD_DIR,
    HARDCODED_YEARS,
    ExportScraperConfig,
    configure_logging,
    run_export_scraper,
)

CONFIG = ExportScraperConfig(
    link_id="SupportingData_CCRGradRate_Link",
    export_button_id="CPH_ReportCard_SupportingDataContent_btnCCRGradRateDataCSVExport_CD",
    dataset_slug="graduation_rate",
    source_name_hint="GradRate",
    page_label="Graduation Rate",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export ALSDE Graduation Rate CSV data for requested years."
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
    run_export_scraper(
        config=CONFIG,
        target_years=target_years,
        headless=not args.headed,
        download_dir=Path(args.download_dir).resolve(),
    )


if __name__ == "__main__":
    main()
