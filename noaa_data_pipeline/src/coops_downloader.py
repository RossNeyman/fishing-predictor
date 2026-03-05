"""
coops_downloader.py — NOAA CO-OPS (Tides & Currents) data downloader.

Downloads one product × one station × one month at a time, saves as Parquet.
Skips files that already exist on disk.
"""

import logging
from datetime import date

import pandas as pd

from utils import (
    coops_parquet_path,
    ensure_parent,
    get_with_retry,
    iter_months,
    polite_sleep,
)

logger = logging.getLogger(__name__)

COOPS_API_BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
COOPS_META_BASE = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations"

# Default request parameters
DEFAULT_DATUM = "MLLW"
DEFAULT_UNITS = "metric"
DEFAULT_TIME_ZONE = "gmt"
APPLICATION_NAME = "ny_fishing_model"


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def download_coops_station(
    station_id: str,
    products: list[str],
    start_date: date,
    end_date: date,
) -> None:
    """
    Download all requested products for one CO-OPS station over the given
    date range, chunked monthly and saved as Parquet.

    Parameters
    ----------
    station_id  : CO-OPS station identifier, e.g. "8516945"
    products    : list of product names, e.g. ["water_level", "wind"]
    start_date  : first day of the requested range (inclusive)
    end_date    : last day of the requested range (inclusive)
    """
    logger.info("CO-OPS station %s — starting download", station_id)

    for product in products:
        logger.info("  product: %s", product)
        for chunk_start, chunk_end in iter_months(start_date, end_date):
            _download_month(station_id, product, chunk_start, chunk_end)

    logger.info("CO-OPS station %s — done", station_id)


def fetch_coops_metadata(station_id: str) -> dict:
    """
    Fetch station metadata from the NOAA MDAPI.

    Returns the raw JSON dict, which includes coordinates, available products,
    sensor info, and platform type keywords.
    """
    url = f"{COOPS_META_BASE}/{station_id}.json"
    try:
        response = get_with_retry(url)
        return response.json()
    except Exception as exc:
        logger.error("Failed to fetch metadata for station %s: %s", station_id, exc)
        return {}


DEFAULT_COOPS_START = date(1980, 1, 1)

# Observational products we want to download.
# Excludes non-observational types: predictions, datums, high_low,
# hourly_height, monthly_mean, annual_flood_mean, etc.
OBSERVATIONAL_PRODUCTS = {
    "water_level",
    "water_temperature",
    "air_temperature",
    "air_pressure",
    "wind",
    "humidity",
    "visibility",
    "currents",
    "salinity",
    "conductivity",
}


def fetch_coops_available_products(station_id: str) -> list[str]:
    """
    Query the MDAPI products endpoint and return the list of observational
    products available at this station.

    Falls back to ["water_level"] on any error.
    """
    url = f"{COOPS_META_BASE}/{station_id}/products.json"
    try:
        response = get_with_retry(url)
        data = response.json()
        all_products = [
            p["name"].lower()
            for p in data.get("products", [])
            if isinstance(p, dict) and "name" in p
        ]
        available = [p for p in all_products if p in OBSERVATIONAL_PRODUCTS]
        if available:
            logger.info("Station %s available products: %s", station_id, available)
            return available
        logger.warning(
            "Station %s: no recognised observational products found in MDAPI — "
            "falling back to water_level",
            station_id,
        )
    except Exception as exc:
        logger.warning(
            "Could not fetch products for station %s: %s — falling back to water_level",
            station_id, exc,
        )
    return ["water_level"]


def fetch_coops_start_date(station_id: str) -> date:
    """
    Return the earliest date for which CO-OPS data is likely available,
    by reading the station's 'established' field from the MDAPI.

    Falls back to DEFAULT_COOPS_START (1980-01-01) on any error.
    """
    meta = fetch_coops_metadata(station_id)
    try:
        established_str = (
            meta.get("stations", [{}])[0]
                .get("details", {})
                .get("established", "")
        )
        if established_str:
            # Format is typically "YYYY-MM-DDTHH:MM:SS" or "YYYY-MM-DD"
            established_date = date.fromisoformat(established_str[:10])
            logger.info(
                "Station %s established: %s", station_id, established_date
            )
            return established_date
    except Exception as exc:
        logger.warning(
            "Could not parse established date for station %s: %s — using fallback %s",
            station_id, exc, DEFAULT_COOPS_START,
        )
    return DEFAULT_COOPS_START


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _download_month(
    station_id: str,
    product: str,
    start: date,
    end: date,
) -> None:
    """Download one month of one product for one station."""
    out_path = coops_parquet_path(station_id, product, start.year, start.month)

    if out_path.exists():
        logger.debug(
            "    Skipping %s/%s %d-%02d (file exists)",
            station_id, product, start.year, start.month,
        )
        return

    logger.info(
        "    Downloading %s/%s  %s → %s",
        station_id, product, start.isoformat(), end.isoformat(),
    )

    params = {
        "product": product,
        "station": station_id,
        "begin_date": start.strftime("%Y%m%d"),
        "end_date": end.strftime("%Y%m%d"),
        "datum": DEFAULT_DATUM,
        "units": DEFAULT_UNITS,
        "time_zone": DEFAULT_TIME_ZONE,
        "format": "json",
        "application": APPLICATION_NAME,
    }

    try:
        response = get_with_retry(COOPS_API_BASE, params=params)
    except Exception as exc:
        logger.error(
            "    HTTP error for %s/%s %d-%02d: %s",
            station_id, product, start.year, start.month, exc,
        )
        polite_sleep(2.0)  # back off longer after a hard failure
        return

    polite_sleep()  # 0.5 s between every successful request

    payload = response.json()

    # The CO-OPS API signals errors inside the JSON body
    if "error" in payload:
        logger.warning(
            "    API error for %s/%s %d-%02d: %s",
            station_id, product, start.year, start.month,
            payload["error"].get("message", payload["error"]),
        )
        return

    df = _parse_coops_response(payload, station_id, product)
    if df.empty:
        logger.warning(
            "    No data rows for %s/%s %d-%02d — skipping write",
            station_id, product, start.year, start.month,
        )
        return

    ensure_parent(out_path)
    df.to_parquet(out_path, index=False)
    logger.info("    Saved %d rows → %s", len(df), out_path)


def _parse_coops_response(payload: dict, station_id: str, product: str) -> pd.DataFrame:
    """
    Convert a raw CO-OPS JSON response into a normalised DataFrame.

    Expected JSON structure (most products):
        { "data": [ {"t": "2024-01-01 00:00", "v": "1.234", ...}, ... ] }

    Currents product uses "data" with "s" (speed) and "d" (direction).

    Returns a DataFrame with columns:
        timestamp, station_id, product, value, [extra columns per product]
    """
    rows = payload.get("data", [])
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Rename the timestamp column
    if "t" in df.columns:
        df = df.rename(columns={"t": "timestamp"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=False)

    df["station_id"] = station_id
    df["product"] = product

    # Coerce the primary value column to numeric
    if "v" in df.columns:
        df["value"] = pd.to_numeric(df["v"], errors="coerce")
        df = df.drop(columns=["v"])

    # Keep quality flag if present
    if "q" in df.columns:
        df = df.rename(columns={"q": "quality_flag"})

    # Currents: keep speed and direction
    for col, new_name in [("s", "speed"), ("d", "direction")]:
        if col in df.columns:
            df[new_name] = pd.to_numeric(df[col], errors="coerce")
            df = df.drop(columns=[col])

    # Drop any remaining raw single-letter columns we don't need
    single_letter = [c for c in df.columns if len(c) == 1]
    if single_letter:
        df = df.drop(columns=single_letter)

    # Normalise column order: put metadata first
    first_cols = [c for c in ["timestamp", "station_id", "product"] if c in df.columns]
    other_cols = [c for c in df.columns if c not in first_cols]
    df = df[first_cols + other_cols]

    return df
