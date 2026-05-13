import os
import sys
import unittest

import gradio as gr


sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import AUTO_FIELDS, DISPLAY_LABELS, UI_FIELDS, USER_FIELDS, _auto_fill, build_input_components, build_ui
from schema import build_default_input


class UISmokeTests(unittest.TestCase):
    def test_ui_builds(self) -> None:
        demo = build_ui()
        self.assertIsInstance(demo, gr.Blocks)

    def test_auto_fill_status_default(self) -> None:
        demo = build_ui()
        status_components = [
            component
            for component in demo.blocks.values()
            if getattr(component, "label", None) == "Auto-fill status"
        ]
        self.assertEqual(len(status_components), 1)
        self.assertEqual(
            status_components[0].value,
            "Auto-fill not completed for NYC forecast.",
        )

    def test_inputs_match_schema(self) -> None:
        with gr.Blocks():
            components = build_input_components()
        self.assertEqual(len(components), len(UI_FIELDS))

    def test_input_labels_match_schema(self) -> None:
        with gr.Blocks():
            components = build_input_components()
        labels = [component.label for component in components]
        expected = [DISPLAY_LABELS.get(field.name, field.name) for field in UI_FIELDS]
        self.assertEqual(labels, expected)

    def test_year_hidden_from_ui(self) -> None:
        field_names = [field.name for field in UI_FIELDS]
        self.assertNotIn("year", field_names)

    def test_auto_fill_updates_values(self) -> None:
        user_values = [build_default_input()[field.name] for field in USER_FIELDS]
        advanced_values = [build_default_input()[field.name] for field in UI_FIELDS]
        updated = build_default_input()
        updated["avg_wind_speed"] = 9.9
        updated["avg_air_pressure"] = 999.0

        with unittest.mock.patch("app.ForecastClient") as mock_client:
            mock_client.return_value.fetch_forecast.return_value = {"hours": []}
            with unittest.mock.patch("app.generate_features", return_value=updated):
                results = _auto_fill(False, build_default_input(), *user_values, *advanced_values)

        expected_length = len(UI_FIELDS) + len(AUTO_FIELDS) + 2
        self.assertEqual(len(results), expected_length)
        wind_update = results[[field.name for field in UI_FIELDS].index("avg_wind_speed")]
        pressure_update = results[[field.name for field in UI_FIELDS].index("avg_air_pressure")]
        self.assertEqual(wind_update["value"], 9.9)
        self.assertEqual(pressure_update["value"], 999.0)
        display_offset = len(UI_FIELDS)
        display_names = [field.name for field in AUTO_FIELDS]
        wind_display = results[display_offset + display_names.index("avg_wind_speed")]["value"]
        self.assertIn("avg_wind_speed", wind_display)
        self.assertIn("9.900", wind_display)


if __name__ == "__main__":
    unittest.main()
