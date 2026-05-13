from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


NYC_LATITUDE = 40.7128
NYC_LONGITUDE = -74.0060


@dataclass(frozen=True)
class ForecastClientConfig:
    provider: str = "open_meteo"
    api_key_env: str = "NYC_FORECAST_API_KEY"
    api_key: str | None = None
    latitude: float = NYC_LATITUDE
    longitude: float = NYC_LONGITUDE
    timezone: str = "UTC"


class ForecastClient:
    def __init__(self, config: ForecastClientConfig | None = None) -> None:
        self._config = config or ForecastClientConfig()

    def fetch_forecast(self, hours_ahead: float) -> dict[str, Any]:
        if hours_ahead <= 0:
            raise ValueError("hours_ahead must be positive")

        provider = self._config.provider.lower()
        if provider == "open_meteo":
            return self._fetch_open_meteo(hours_ahead)
        if provider == "weatherapi":
            api_key = self._get_api_key()
            raise NotImplementedError(f"Provider '{provider}' not implemented (api key: {bool(api_key)})")
        raise ValueError(f"Unsupported provider: {self._config.provider}")

    def _get_api_key(self) -> str:
        api_key = self._config.api_key or os.getenv(self._config.api_key_env)
        if not api_key:
            raise ValueError(f"Missing API key for provider {self._config.provider}")
        return api_key

    def _fetch_open_meteo(self, hours_ahead: float) -> dict[str, Any]:
        params = {
            "latitude": self._config.latitude,
            "longitude": self._config.longitude,
            "hourly": "temperature_2m,pressure_msl,wind_speed_10m,wind_gusts_10m",
            "forecast_days": 2,
            "timezone": self._config.timezone,
        }
        url = f"https://api.open-meteo.com/v1/forecast?{urlencode(params)}"

        with urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))

        hourly = payload.get("hourly")
        if not isinstance(hourly, dict):
            raise ValueError("Forecast response missing hourly data")

        times = hourly.get("time")
        wind_speed = hourly.get("wind_speed_10m")
        wind_gust = hourly.get("wind_gusts_10m")
        air_pressure = hourly.get("pressure_msl")
        air_temp_c = hourly.get("temperature_2m")

        if not all(isinstance(series, list) for series in [times, wind_speed, wind_gust, air_pressure, air_temp_c]):
            raise ValueError("Forecast response missing required hourly series")

        num_points = int(math.ceil(hours_ahead))
        if len(times) < num_points:
            raise ValueError("Not enough forecast data for requested window")

        hours: list[dict[str, Any]] = []
        for idx in range(num_points):
            hours.append(
                {
                    "time": times[idx],
                    "wind_speed": wind_speed[idx],
                    "wind_gust": wind_gust[idx],
                    "air_pressure": air_pressure[idx],
                    "air_temp_c": air_temp_c[idx],
                    "water_temp_c": None,
                    "water_level": None,
                }
            )

        return {
            "provider": "open_meteo",
            "latitude": self._config.latitude,
            "longitude": self._config.longitude,
            "timezone": self._config.timezone,
            "hours": hours,
        }
