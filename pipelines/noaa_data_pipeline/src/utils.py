"""
utils.py — Shared utilities for the NOAA data pipeline.

Includes:
  - monthly date range chunking
  - retry-with-backoff HTTP requests
  - parquet file path resolution
  - logging setup
"""

import calendar
import logging
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Generator

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Root data directory (noaa_data_pipeline/data/)
# ---------------------------------------------------------------------------
DATA_ROOT = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# Date utilities
# ---------------------------------------------------------------------------

def iter_months(start: date, end: date) -> Generator[tuple[date, date], None, None]:
    """
    Yield (month_start, month_end) tuples covering the range [start, end].

    Parameters
    ----------
    start, end : datetime.date
        Inclusive date range.

    Yields
    ------
    (first_day_of_month, last_day_of_month) pairs.
    """
    current = start.replace(day=1)
    end_month_first = end.replace(day=1)

    while current <= end_month_first:
        last_day = calendar.monthrange(current.year, current.month)[1]
        month_end = current.replace(day=last_day)
        # Clip to the requested range
        chunk_start = max(current, start)
        chunk_end = min(month_end, end)
        yield chunk_start, chunk_end
        # Advance to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)


# ---------------------------------------------------------------------------
# HTTP retry utility
# ---------------------------------------------------------------------------

def get_with_retry(
    url: str,
    params: dict | None = None,
    max_retries: int = 3,
    backoff_base: float = 2.0,
    timeout: int = 60,
) -> requests.Response:
    """
    GET a URL with exponential-backoff retry.

    Parameters
    ----------
    url          : request URL
    params       : query parameters dict
    max_retries  : maximum number of attempts (default 3)
    backoff_base : seconds to wait before first retry; doubles each attempt
    timeout      : per-request timeout in seconds

    Returns
    -------
    requests.Response with status 200.

    Raises
    ------
    requests.HTTPError  if all retries are exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except Exception as exc:
            # Catch both requests.RequestException and raw OSError/ssl.SSLError
            # that can bubble up when the server drops the connection mid-response.
            last_exc = exc
            wait = backoff_base ** (attempt - 1)
            logger.warning(
                "Request failed (attempt %d/%d): %s — retrying in %.1fs",
                attempt,
                max_retries,
                exc,
                wait,
            )
            if attempt < max_retries:
                time.sleep(wait)

    raise requests.HTTPError(
        f"All {max_retries} attempts failed for {url}"
    ) from last_exc


def polite_sleep(seconds: float = 2) -> None:
    """Sleep briefly between API requests to avoid overwhelming the NOAA servers."""
    time.sleep(seconds)


# ---------------------------------------------------------------------------
# File path helpers
# ---------------------------------------------------------------------------

def coops_parquet_path(
    station_id: str,
    product: str,
    year: int,
    month: int,
    data_root: Path | None = None,
) -> Path:
    """
    Return the canonical parquet path for a CO-OPS observation chunk.

    Layout:
        data/source=coops/station={id}/product={product}/year={year}/month={mm}.parquet
    """
    root = data_root or DATA_ROOT
    return (
        root
        / f"source=coops"
        / f"station={station_id}"
        / f"product={product}"
        / f"year={year}"
        / f"month={month:02d}.parquet"
    )


def ndbc_parquet_path(
    station_id: str,
    year: int,
    data_root: Path | None = None,
) -> Path:
    """
    Return the canonical parquet path for an NDBC observation year.

    Layout:
        data/source=ndbc/station={id}/year={year}/data.parquet
    """
    root = data_root or DATA_ROOT
    return (
        root
        / f"source=ndbc"
        / f"station={station_id}"
        / f"year={year}"
        / "data.parquet"
    )


def ensure_parent(path: Path) -> Path:
    """Create parent directories then return the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with a timestamped console handler."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
