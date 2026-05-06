"""
pipeline.py — Top-level orchestrator for the NOAA data pipeline.

Usage
-----
    python pipeline.py --start 2020-01-01 --end 2024-12-31
    python pipeline.py --start 2024-01-01 --end 2024-12-31 --only coops
    python pipeline.py --all-history
    python pipeline.py --all-history --only ndbc
    python pipeline.py --all-history --end 2024-12-31
"""

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

# Allow running from the repo root: python noaa_data_pipeline/src/pipeline.py
sys.path.insert(0, str(Path(__file__).parent))

from stations import load_stations, get_ndbc_station_ids, get_coops_stations
from coops_downloader import download_coops_station, fetch_coops_start_date, fetch_coops_available_products
from ndbc_downloader import download_ndbc_station
from utils import setup_logging

# Earliest year NDBC has archive data for any station
NDBC_HISTORY_START = date(1970, 1, 1)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def download_all_stations(
    config_path: Path | str | None = None,
    start_date: date = date(2020, 1, 1),
    end_date: date = date.today(),
    run_coops: bool = True,
    run_ndbc: bool = True,
    all_history: bool = False,
) -> None:
    """
    Download data for all stations defined in the station config.

    Parameters
    ----------
    config_path : path to stations.json (default: noaa_data_pipeline/config/stations.json)
    start_date  : first day of the requested download range (ignored when all_history=True)
    end_date    : last  day of the requested download range
    run_coops   : whether to download CO-OPS stations
    run_ndbc    : whether to download NDBC stations
    all_history : when True, automatically determine the earliest available date
                  for each station instead of using start_date
    """
    config = load_stations(config_path)
    region = config.get("region", "unknown")
    logger.info("=== NOAA Data Pipeline — region: %s ===", region)
    if all_history:
        logger.info("Mode: full history  end=%s", end_date)
    else:
        logger.info("Date range: %s → %s", start_date, end_date)

    errors: list[str] = []

    # ------------------------------------------------------------------
    # CO-OPS stations
    # ------------------------------------------------------------------
    if run_coops:
        coops_stations = get_coops_stations(config)
        logger.info("CO-OPS stations to process: %d", len(coops_stations))

        for station in coops_stations:
            sid = station["id"]
            name = station.get("name", "")
            logger.info("--- CO-OPS %s (%s) ---", sid, name)
            products = fetch_coops_available_products(sid)
            effective_start = fetch_coops_start_date(sid) if all_history else start_date
            try:
                download_coops_station(sid, products, effective_start, end_date)
            except Exception as exc:
                msg = f"CO-OPS station {sid} failed: {exc}"
                logger.error(msg)
                errors.append(msg)

    # ------------------------------------------------------------------
    # NDBC stations
    # ------------------------------------------------------------------
    if run_ndbc:
        ndbc_ids = get_ndbc_station_ids(config)
        logger.info("NDBC stations to process: %d", len(ndbc_ids))

        for sid in ndbc_ids:
            logger.info("--- NDBC %s ---", sid)
            effective_start = NDBC_HISTORY_START if all_history else start_date
            try:
                download_ndbc_station(sid, effective_start, end_date)
            except Exception as exc:
                msg = f"NDBC station {sid} failed: {exc}"
                logger.error(msg)
                errors.append(msg)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    logger.info("=== Pipeline complete. Errors: %d ===", len(errors))
    for err in errors:
        logger.error("  %s", err)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download NOAA marine environmental data for the New York region."
    )
    parser.add_argument(
        "--start",
        default=None,
        metavar="YYYY-MM-DD",
        help="Start date (inclusive). Required unless --all-history is set.",
    )
    parser.add_argument(
        "--end",
        default=date.today().isoformat(),
        metavar="YYYY-MM-DD",
        help="End date (inclusive). Defaults to today.",
    )
    parser.add_argument(
        "--all-history",
        action="store_true",
        help=(
            "Download the full available history for each station. "
            "For CO-OPS stations the established date is fetched automatically. "
            "For NDBC stations the archive is tried from 1970 onward. "
            "Overrides --start."
        ),
    )
    parser.add_argument(
        "--station-config",
        default=None,
        metavar="PATH",
        help="Path to stations.json. Defaults to config/stations.json.",
    )
    parser.add_argument(
        "--only",
        choices=["coops", "ndbc"],
        default=None,
        help="Restrict download to a single source type.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    setup_logging(level=getattr(logging, args.log_level))

    if not args.all_history and args.start is None:
        logger.error("--start is required unless --all-history is set.")
        sys.exit(1)

    try:
        start = date.fromisoformat(args.start) if args.start else date(2020, 1, 1)
        end = date.fromisoformat(args.end)
    except ValueError as exc:
        logger.error("Invalid date: %s", exc)
        sys.exit(1)

    if not args.all_history and start > end:
        logger.error("--start must be before --end")
        sys.exit(1)

    download_all_stations(
        config_path=args.station_config,
        start_date=start,
        end_date=end,
        run_coops=args.only in (None, "coops"),
        run_ndbc=args.only in (None, "ndbc"),
        all_history=args.all_history,
    )


if __name__ == "__main__":
    main()
