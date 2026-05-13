import os
import sys
import unittest
from unittest.mock import MagicMock, patch


sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from feature_engineering import generate_features
from predictor import load_model, predict_from_dict


class AutoFillIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        load_model.cache_clear()

    def test_autofill_forecast_to_prediction(self) -> None:
        forecast = {
            "hours": [
                {
                    "time": "2026-05-12T10:00",
                    "wind_speed": 3.0,
                    "wind_gust": 5.0,
                    "air_pressure": 1014.0,
                    "air_temp_c": 19.0,
                    "water_temp_c": 18.0,
                    "water_level": 1.1,
                },
                {
                    "time": "2026-05-12T11:00",
                    "wind_speed": 4.0,
                    "wind_gust": 6.0,
                    "air_pressure": 1013.0,
                    "air_temp_c": 18.0,
                    "water_temp_c": 18.5,
                    "water_level": 1.2,
                },
            ]
        }
        user_inputs = {
            "FFDAYS2": 1.0,
            "HRSF": 2.0,
            "MODE_F": 7.0,
            "CNTRBTRS": 1.0,
        }

        features = generate_features(forecast, user_inputs)

        mock_model = MagicMock()
        mock_model.predict.return_value = [1]
        mock_model.predict_proba.return_value = [[0.25, 0.75]]
        mock_model.classes_ = [0, 1]

        with patch("predictor.joblib.load", return_value=mock_model):
            label, probability = predict_from_dict(features)

        self.assertEqual(label, 1)
        self.assertAlmostEqual(probability or 0.0, 0.75, places=6)


if __name__ == "__main__":
    unittest.main()
