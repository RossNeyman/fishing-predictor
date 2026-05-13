import os
import sys
import unittest


sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from feature_engineering import generate_features
from schema import SCHEMA_INDEX


class FeatureEngineeringTests(unittest.TestCase):
    def test_generate_features_uses_forecast_window_and_user_inputs(self) -> None:
        forecast = {
            "hours": [
                {
                    "time": "2026-05-12T10:00",
                    "wind_speed": 2.0,
                    "wind_gust": 4.0,
                    "air_pressure": 1015.0,
                    "air_temp_c": 20.0,
                    "water_temp_c": 18.0,
                    "water_level": 1.0,
                },
                {
                    "time": "2026-05-12T11:00",
                    "wind_speed": 4.0,
                    "wind_gust": 6.0,
                    "air_pressure": 1012.0,
                    "air_temp_c": 16.0,
                    "water_temp_c": 19.0,
                    "water_level": 1.2,
                },
                {
                    "time": "2026-05-12T12:00",
                    "wind_speed": 10.0,
                    "wind_gust": 12.0,
                    "air_pressure": 1010.0,
                    "air_temp_c": 10.0,
                    "water_temp_c": 20.0,
                    "water_level": 1.5,
                },
            ]
        }

        data = generate_features(
            forecast,
            {
                "FFDAYS2": 2.0,
                "HRSF": 2.0,
                "MODE_F": 7.0,
                "CNTRBTRS": 1.0,
                "IMP_REC": 1.0,
            },
        )

        self.assertEqual(data["IMP_REC"], 0.0)
        self.assertAlmostEqual(data["avg_wind_speed"], 3.0, places=6)
        self.assertAlmostEqual(data["avg_wind_gust"], 5.0, places=6)
        self.assertEqual(data["wind_speed_rose"], 1)
        self.assertEqual(data["wind_speed_fell"], 0)
        self.assertEqual(data["air_pressure_fell"], 1)
        self.assertEqual(data["storm_approaching"], 1)
        self.assertEqual(data["cold_front"], 1)
        self.assertAlmostEqual(data["temp_diff"], -0.5, places=6)
        self.assertAlmostEqual(data["temp_shock_magnitude"], 0.5, places=6)
        self.assertEqual(data["water_is_moving"], 1)
        self.assertAlmostEqual(data["wind_x_pressure"], 3.0 * 1013.5, places=6)
        self.assertAlmostEqual(data["gust_ratio"], 5.0 / 3.0, places=6)
        self.assertAlmostEqual(data["total_effort_hours"], 4.0, places=6)
        self.assertEqual(data["year"], 2024)
        self.assertEqual(data["month"], 5)
        self.assertEqual(data["day"], 12)
        self.assertEqual(data["hour"], 10)

    def test_generate_features_falls_back_to_defaults(self) -> None:
        forecast = {
            "hours": [
                {
                    "time": "2026-05-12T10:00",
                    "wind_speed": 2.0,
                    "wind_gust": 4.0,
                    "air_pressure": 1015.0,
                    "air_temp_c": 20.0,
                    "water_temp_c": None,
                    "water_level": None,
                },
                {
                    "time": "2026-05-12T11:00",
                    "wind_speed": 2.0,
                    "wind_gust": 4.0,
                    "air_pressure": 1015.0,
                    "air_temp_c": 20.0,
                    "water_temp_c": None,
                    "water_level": None,
                },
            ]
        }

        data = generate_features(
            forecast,
            {
                "FFDAYS2": 1.0,
                "HRSF": 2.0,
                "MODE_F": 7.0,
                "CNTRBTRS": 1.0,
            },
        )

        self.assertEqual(data["avg_water_temp_c"], SCHEMA_INDEX["avg_water_temp_c"].default)
        self.assertEqual(data["avg_water_level"], SCHEMA_INDEX["avg_water_level"].default)


if __name__ == "__main__":
    unittest.main()
