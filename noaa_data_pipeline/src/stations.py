"""
stations.py — Station configuration loader.

Loads stations.json and returns structured lists of NDBC and CO-OPS stations.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default path relative to this file's location
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "stations.json"


def load_stations(config_path: Path | str | None = None) -> dict[str, Any]:
    """
    Load and validate the station configuration file.

    Parameters
    ----------
    config_path : path-like, optional
        Path to stations.json.  Defaults to noaa_data_pipeline/config/stations.json.

    Returns
    -------
    dict with keys:
        "region"  – str
        "ndbc"    – list[str]  station IDs
        "coops"   – list[dict] each with "id", "name", "products"
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

    if not path.exists():
        raise FileNotFoundError(f"Station config not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        config = json.load(fh)

    _validate_config(config)
    logger.info(
        "Loaded station config: region=%s, ndbc=%d, coops=%d",
        config.get("region"),
        len(config.get("ndbc", [])),
        len(config.get("coops", [])),
    )
    return config


def _validate_config(config: dict) -> None:
    """Raise ValueError if the config is missing required fields."""
    if not isinstance(config, dict):
        raise ValueError("Station config must be a JSON object.")

    for field in ("ndbc", "coops"):
        if field not in config:
            raise ValueError(f"Station config missing required field: '{field}'")

    if not isinstance(config["ndbc"], list):
        raise ValueError("'ndbc' must be a list of station ID strings.")

    if not isinstance(config["coops"], list):
        raise ValueError("'coops' must be a list of station objects.")

    for entry in config["coops"]:
        if not isinstance(entry, dict) or "id" not in entry:
            raise ValueError(
                f"Each CO-OPS entry must be an object with at least an 'id' field. "
                f"Got: {entry!r}"
            )


def get_ndbc_station_ids(config: dict) -> list[str]:
    """Return the list of NDBC station ID strings."""
    return [str(s) for s in config["ndbc"]]


def get_coops_stations(config: dict) -> list[dict]:
    """Return the list of CO-OPS station dicts."""
    return config["coops"]


def get_coops_products(station: dict) -> list[str]:
    """Return the products list for a CO-OPS station dict, defaulting to water_level."""
    return station.get("products", ["water_level"])
