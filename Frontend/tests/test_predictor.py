import os
import sys
import unittest
from unittest.mock import MagicMock, patch


sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from predictor import load_model, predict_from_dict
from schema import build_default_input


class PredictorTests(unittest.TestCase):
    def setUp(self) -> None:
        load_model.cache_clear()

    def test_predict_from_dict_returns_label_and_probability(self) -> None:
        mock_model = MagicMock()
        mock_model.predict.return_value = [1]
        mock_model.predict_proba.return_value = [[0.2, 0.8]]
        mock_model.classes_ = [0, 1]

        with patch("predictor.joblib.load", return_value=mock_model):
            label, probability = predict_from_dict(build_default_input())

        self.assertEqual(label, 1)
        self.assertAlmostEqual(probability or 0.0, 0.8, places=6)

    def test_predict_from_dict_validates_input(self) -> None:
        mock_model = MagicMock()
        mock_model.predict.return_value = [0]

        with patch("predictor.joblib.load", return_value=mock_model):
            data = build_default_input()
            data["year"] = 1900
            with self.assertRaises(ValueError):
                predict_from_dict(data)


if __name__ == "__main__":
    unittest.main()
