import json
import os
import sys
import unittest
from unittest.mock import patch


sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from forecast import ForecastClient, ForecastClientConfig


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class ForecastClientTests(unittest.TestCase):
    def test_fetch_open_meteo_success(self) -> None:
        payload = {
            "hourly": {
                "time": ["2026-05-12T10:00", "2026-05-12T11:00"],
                "wind_speed_10m": [3.2, 4.1],
                "wind_gusts_10m": [5.0, 6.3],
                "pressure_msl": [1014.0, 1013.2],
                "temperature_2m": [18.2, 18.8],
            }
        }

        with patch("forecast.urlopen", return_value=FakeResponse(payload)):
            client = ForecastClient(ForecastClientConfig(provider="open_meteo"))
            data = client.fetch_forecast(2)

        self.assertEqual(data["provider"], "open_meteo")
        self.assertEqual(len(data["hours"]), 2)
        self.assertEqual(data["hours"][0]["wind_speed"], 3.2)
        self.assertIsNone(data["hours"][0]["water_temp_c"])

    def test_fetch_open_meteo_missing_series_raises(self) -> None:
        payload = {"hourly": {"time": ["2026-05-12T10:00"]}}
        with patch("forecast.urlopen", return_value=FakeResponse(payload)):
            client = ForecastClient(ForecastClientConfig(provider="open_meteo"))
            with self.assertRaises(ValueError):
                client.fetch_forecast(1)

    def test_unknown_provider_raises(self) -> None:
        client = ForecastClient(ForecastClientConfig(provider="unknown"))
        with self.assertRaises(ValueError):
            client.fetch_forecast(1)

    def test_provider_requires_api_key(self) -> None:
        client = ForecastClient(ForecastClientConfig(provider="weatherapi", api_key=None))
        with self.assertRaises(ValueError):
            client.fetch_forecast(1)


if __name__ == "__main__":
    unittest.main()
