from __future__ import annotations

import argparse
import logging
from pathlib import Path

from pipeline.alsde_supporting_data import student_demographics_nav
from pipeline.alsde_supporting_data.export_scraper_common import (
    DEFAULT_DOWNLOAD_DIR,
    HARDCODED_YEARS,
    ExportScraperConfig,
    configure_logging,
    run_export_scraper,
)

logger = logging.getLogger(__name__)

ALL_DATASET_CONFIGS: tuple[ExportScraperConfig, ...] = (
    ExportScraperConfig(
        link_id="SupportingData_CCRGradRate_Link",
        export_button_id="CPH_ReportCard_SupportingDataContent_btnCCRGradRateDataCSVExport_CD",
        dataset_slug="graduation_rate",
        source_name_hint="GradRate",
        page_label="Graduation Rate",
    ),
    ExportScraperConfig(
        link_id="SupportingData_Educator_Demographics_Link",
        export_button_id="CPH_ReportCard_SupportingDataContent_btnEducatorDemographicsDataCSVExport_CD",
        dataset_slug="educator_demographics",
        source_name_hint="EducatorDemographics",
        page_label="Educator Demographics",
    ),
    ExportScraperConfig(
        link_id="SupportingData_Educator_Experienced_Link",
        export_button_id="CPH_ReportCard_SupportingDataContent_btnExperiencedEducatorDataCSVExport_CD",
        dataset_slug="educator_experience",
        source_name_hint="ExperiencedEducator",
        page_label="Educator Experience",
    ),
    ExportScraperConfig(
        link_id="SupportingData_Educator_Credentials_Link",
        export_button_id="CPH_ReportCard_SupportingDataContent_btnEducatorCredentialsDataCSVExport_CD",
        dataset_slug="educator_credentials",
        source_name_hint="EducatorCredentials",
        page_label="Educator Credentials",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run all ALSDE supporting-data export scrapers sequentially."
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
        "--request-wait-seconds",
        type=float,
        default=2.0,
        help="Pause between demographics filter/export requests (default: 2.0).",
    )
    parser.add_argument(
        "--system-limit",
        type=int,
        default=None,
        help="Optional cap on prefix bins per year for student demographics.",
    )
    parser.add_argument(
        "--prefix-target-size",
        type=int,
        default=8,
        help="Target number of systems per student demographics prefix bin.",
    )
    parser.add_argument(
        "--max-prefix-length",
        type=int,
        default=5,
        help="Maximum prefix length for student demographics bins.",
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
    download_dir = Path(args.download_dir).resolve()

    failures: list[str] = []
    try:
        student_demographics_nav.run(
            target_years=target_years,
            headless=not args.headed,
            download_dir=download_dir,
            request_wait_seconds=args.request_wait_seconds,
            system_limit=args.system_limit,
            prefix_target_size=args.prefix_target_size,
            max_prefix_length=args.max_prefix_length,
        )
    except Exception as exc:
        failures.append("Student Demographics")
        logger.error("Student Demographics failed: %s", exc)

    for config in ALL_DATASET_CONFIGS:
        try:
            run_export_scraper(
                config=config,
                target_years=target_years,
                headless=not args.headed,
                download_dir=download_dir,
            )
        except Exception as exc:
            failures.append(config.page_label)
            logger.error("%s failed: %s", config.page_label, exc)

    if failures:
        logger.error(
            "Completed with failures (%s/%s): %s",
            len(failures),
            len(ALL_DATASET_CONFIGS) + 1,
            failures,
        )
        raise SystemExit(1)

    logger.info(
        "All %s dataset scrapers completed successfully",
        len(ALL_DATASET_CONFIGS) + 1,
    )


if __name__ == "__main__":
    main()
