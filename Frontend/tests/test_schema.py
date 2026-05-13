import os
import sys
import unittest


sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from schema import build_default_input, validate_input


class SchemaValidationTests(unittest.TestCase):
    def test_defaults_are_valid(self) -> None:
        data = build_default_input()
        validate_input(data)

    def test_missing_field_raises(self) -> None:
        data = build_default_input()
        data.pop("avg_wind_speed")
        with self.assertRaises(ValueError):
            validate_input(data)

    def test_out_of_range_raises(self) -> None:
        data = build_default_input()
        data["year"] = 1900
        with self.assertRaises(ValueError):
            validate_input(data)

    def test_wrong_type_raises(self) -> None:
        data = build_default_input()
        data["month"] = "July"
        with self.assertRaises(ValueError):
            validate_input(data)


if __name__ == "__main__":
    unittest.main()
