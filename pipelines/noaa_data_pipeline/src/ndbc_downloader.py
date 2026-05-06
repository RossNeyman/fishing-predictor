"""
ndbc_downloader.py — NOAA NDBC buoy data downloader.

Downloads annual historical standard meteorological data files from the
NDBC archive, parses them, and stores monthly Parquet files.

NDBC archive URL pattern:
    https://www.ndbc.noaa.gov/data/historical/stdmet/{station}h{year}.txt.gz

Column reference (stdmet format):
    https://www.ndbc.noaa.gov/measdes.shtml
"""

import io
import logging
from datetime import date, datetime

import pandas as pd
import requests

from utils import (
    ensure_parent,
    get_with_retry,
    ndbc_parquet_path,
)

logger = logging.getLogger(__name__)

NDBC_ARCHIVE_BASE = "https://www.ndbc.noaa.gov/data/historical/stdmet"
NDBC_REALTIME_BASE = "https://www.ndbc.noaa.gov/data/realtime2"

# Sentinel values used by NDBC to represent missing data
NDBC_MISSING_VALUES = {99.0, 999.0, 9999.0, 99.00, 999.00, 9999.00}

# Mapping from raw NDBC column names to friendlier names
COLUMN_RENAME = {
    "WDIR": "wind_direction_deg",
    "WSPD": "wind_speed_ms",
    "GST": "wind_gust_ms",
    "WVHT": "wave_height_m",
    "DPD": "dominant_wave_period_s",
    "APD": "avg_wave_period_s",
    "MWD": "wave_direction_deg",
    "PRES": "air_pressure_hpa",
    "ATMP": "air_temp_c",
    "WTMP": "water_temp_c",
    "DEWP": "dewpoint_c",
    "VIS": "visibility_nm",
    "PTDY": "pressure_tendency_hpa",
    "TIDE": "water_level_ft",
}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def download_ndbc_station(
    station_id: str,
    start_date: date,
    end_date: date,
) -> None:
    """
    Download historical NDBC data for one station over the given date range,
    stored as one Parquet file per year.

    Parameters
    ----------
    station_id : NDBC station identifier, e.g. "44025"
    start_date : first day of the requested range (inclusive)
    end_date   : last day of the requested range (inclusive)
    """
    logger.info("NDBC station %s — starting download", station_id)

    years = range(start_date.year, end_date.year + 1)
    for year in years:
        _download_year(station_id, year)

    logger.info("NDBC station %s — done", station_id)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _download_year(station_id: str, year: int) -> None:
    """Download and store one year of stdmet data for one NDBC station."""
    out_path = ndbc_parquet_path(station_id, year)

    if out_path.exists():
        logger.debug("  Skipping %s year=%d (file exists)", station_id, year)
        return

    logger.info("  Downloading NDBC %s year=%d", station_id, year)

    raw_text = _fetch_ndbc_stdmet(station_id, year)
    if raw_text is None:
        return

    df = _parse_ndbc_stdmet(raw_text, station_id)
    if df.empty:
        logger.warning("  No data rows for %s year=%d — skipping write", station_id, year)
        return

    ensure_parent(out_path)
    df.to_parquet(out_path, index=False)
    logger.info("  Saved %d rows → %s", len(df), out_path)


def _fetch_ndbc_stdmet(station_id: str, year: int) -> str | None:
    """
    Try to fetch the stdmet historical file for the given station and year.
    Returns the decoded text on success, None on failure.

    The NDBC archive uses station IDs in lowercase for the filename.
    """
    sid = station_id.lower()
    url = f"{NDBC_ARCHIVE_BASE}/{sid}h{year}.txt.gz"

    try:
        response = get_with_retry(url, timeout=120)
        # requests decompresses gzip automatically when Content-Encoding is set;
        # for .txt.gz files we may need to decompress manually.
        import gzip

        try:
            content = gzip.decompress(response.content).decode("utf-8", errors="replace")
        except gzip.BadGzipFile:
            # Some years are served as plain text
            content = response.text

        return content

    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            logger.warning(
                "  NDBC archive file not found: %s (station=%s, year=%d)",
                url, station_id, year,
            )
        else:
            logger.error(
                "  HTTP error fetching NDBC %s year=%d: %s", station_id, year, exc
            )
        return None
    except Exception as exc:
        logger.error("  Unexpected error fetching NDBC %s year=%d: %s", station_id, year, exc)
        return None


def _parse_ndbc_stdmet(raw_text: str, station_id: str) -> pd.DataFrame:
    """
    Parse an NDBC standard meteorological data file into a DataFrame.

    The file format uses two header rows:
        Row 1: column names (e.g. #YY MM DD hh mm WDIR WSPD ...)
        Row 2: units         (e.g. #yr mo dy hr mn m/s m/s ...)

    All NaN sentinel values (99, 999, 9999, …) are replaced with NaN.
    """
    # Split into lines, filter blanks
    lines = [l for l in raw_text.splitlines() if l.strip()]
    if len(lines) < 3:
        return pd.DataFrame()

    # Detect header format: older files use 4-digit year in first col (#YYYY)
    # newer files have #YY (two-digit year).  Both are handled by pandas after
    # we strip the leading '#'.
    header_line = lines[0].lstrip("#").split()
    # Skip the units line (lines[1])
    data_lines = lines[2:]

    try:
        df = pd.read_csv(
            io.StringIO("\n".join(data_lines)),
            delim_whitespace=True,
            header=None,
            names=header_line,
            na_values=["MM"],
            low_memory=False,
        )
    except Exception as exc:
        logger.error("  Failed to parse NDBC text: %s", exc)
        return pd.DataFrame()

    df = _build_timestamp(df)
    if df is None:
        return pd.DataFrame()

    df["station_id"] = station_id

    # Rename to friendly column names
    df = df.rename(columns=COLUMN_RENAME)

    # Replace NDBC sentinel missing values with NaN
    numeric_cols = df.select_dtypes(include="number").columns
    for col in numeric_cols:
        df[col] = df[col].where(~df[col].isin(NDBC_MISSING_VALUES))

    # Reorder: timestamp and station_id first
    first_cols = [c for c in ["timestamp", "station_id"] if c in df.columns]
    other_cols = [c for c in df.columns if c not in first_cols]
    df = df[first_cols + other_cols].reset_index(drop=True)

    return df


def _build_timestamp(df: pd.DataFrame) -> pd.DataFrame | None:
    """
    Combine year/month/day/hour/minute columns into a single UTC timestamp.
    Handles both 4-digit (#YYYY) and 2-digit (#YY) year columns.
    """
    # Normalise year column name
    year_col = None
    for candidate in ("YYYY", "YY", "#YY", "#YYYY"):
        if candidate in df.columns:
            year_col = candidate
            break

    if year_col is None:
        logger.error("  Cannot find year column in NDBC data; columns: %s", df.columns.tolist())
        return None

    try:
        year = df[year_col].astype(int)
        # 2-digit years: 96–99 → 1996–1999, 00–30 → 2000–2030
        if year.max() < 100:
            year = year.where(year >= 50, year + 2000)
            year = year.where(year < 50 + 2000, year + 1900)

        df["timestamp"] = pd.to_datetime(
            {
                "year": year,
                "month": df["MM"].astype(int),
                "day": df["DD"].astype(int),
                "hour": df["hh"].astype(int),
                "minute": df.get("mm", pd.Series([0] * len(df))).astype(int),
            },
            utc=False,
            errors="coerce",
        )

        # Drop raw date columns
        date_cols = [c for c in [year_col, "MM", "DD", "hh", "mm"] if c in df.columns]
        df = df.drop(columns=date_cols)

    except Exception as exc:
        logger.error("  Timestamp construction failed: %s", exc)
        return None

    return df
