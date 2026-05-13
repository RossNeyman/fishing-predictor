import os
import sys
import unittest


sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from predictor import predict_from_dict
from schema import build_default_input


class InferenceIntegrationTests(unittest.TestCase):
    def test_prediction_with_default_input(self) -> None:
        label, probability = predict_from_dict(build_default_input())
        self.assertIsNotNone(label)
        if probability is not None:
            self.assertGreaterEqual(probability, 0.0)
            self.assertLessEqual(probability, 1.0)


if __name__ == "__main__":
    unittest.main()
