from __future__ import annotations

import gradio as gr
from gradio.components import Component

from feature_engineering import generate_features
from forecast import ForecastClient
from predictor import predict_from_dict
from schema import SCHEMA, FieldSpec, build_default_input

USER_INPUT_FIELDS = {"FFDAYS2", "HRSF", "MODE_F", "CNTRBTRS"}
DISPLAY_LABELS = {
    "FFDAYS2": "Days you fished in the last 2 months",
    "HRSF": "How many hours you plan to fish",
    "MODE_F": "Mode of fishing",
    "CNTRBTRS": "Number of people fishing with you",
}
EXCLUDED_FIELDS = {"IMP_REC", "year"}
FIXED_YEAR = 2024
UI_FIELDS = [field for field in SCHEMA if field.name not in EXCLUDED_FIELDS]
USER_FIELDS = [field for field in UI_FIELDS if field.name in USER_INPUT_FIELDS]
AUTO_FIELDS = [field for field in UI_FIELDS if field.name not in USER_INPUT_FIELDS]


def _component_for_field(field: FieldSpec, interactive: bool = True) -> Component:
    label = DISPLAY_LABELS.get(field.name, field.name)
    if field.field_type == "bool":
        return gr.Checkbox(label=label, value=bool(field.default), interactive=interactive)

    if field.field_type == "int":
        return gr.Number(
            label=label,
            value=float(field.default),
            minimum=float(field.min_value),
            maximum=float(field.max_value),
            precision=0,
            step=1.0,
            interactive=interactive,
        )
    return gr.Number(
        label=label,
        value=float(field.default),
        minimum=float(field.min_value),
        maximum=float(field.max_value),
        precision=None,
        interactive=interactive,
    )


def build_input_components() -> list[Component]:
    return [_component_for_field(field, interactive=True) for field in UI_FIELDS]


def build_user_input_components() -> list[Component]:
    return [_component_for_field(field, interactive=True) for field in USER_FIELDS]


def _format_display_value(field: FieldSpec, value: float | int | bool) -> str:
    if field.field_type == "bool":
        return "Yes" if bool(value) else "No"
    if field.field_type == "int":
        return str(int(round(float(value))))
    numeric = float(value)
    if abs(numeric) >= 1000:
        return f"{numeric:,.3f}"
    return f"{numeric:.3f}"


def _display_text(field: FieldSpec, value: float | int | bool) -> str:
    return f"**{field.name}**: {_format_display_value(field, value)}"


def _format_label(label: object) -> str:
    if isinstance(label, bool):
        return "Catch likely" if label else "Catch unlikely"
    if isinstance(label, int):
        return "Catch likely" if label == 1 else "Catch unlikely"
    label_text = str(label).strip().lower()
    if label_text in {"1", "true", "yes", "catch", "has_catch", "positive"}:
        return "Catch likely"
    if label_text in {"0", "false", "no", "no_catch", "negative"}:
        return "Catch unlikely"
    return f"Predicted class: {label}"


def _predict(is_advanced: bool, auto_state: dict[str, object], *values) -> str:
    user_values = values[: len(USER_FIELDS)]
    advanced_values = values[len(USER_FIELDS) :]

    if is_advanced:
        data = {field.name: value for field, value in zip(UI_FIELDS, advanced_values, strict=True)}
    else:
        data = build_default_input()
        if auto_state:
            data.update(auto_state)
        user_inputs = {field.name: value for field, value in zip(USER_FIELDS, user_values, strict=True)}
        data.update(user_inputs)
    data["IMP_REC"] = 0.0
    data["year"] = FIXED_YEAR
    try:
        label, probability = predict_from_dict(data)
    except ValueError as exc:
        return f"Input validation error: {exc}"

    label_text = _format_label(label)
    if probability is None or label_text.startswith("Predicted class:"):
        return label_text
    return f"{label_text} (probability: {probability:.3f})"


def _auto_fill(is_advanced: bool, auto_state: dict[str, object], *values):
    user_values = values[: len(USER_FIELDS)]
    advanced_values = values[len(USER_FIELDS) :]
    if is_advanced:
        data = {field.name: value for field, value in zip(UI_FIELDS, advanced_values, strict=True)}
        user_inputs = {name: data[name] for name in USER_INPUT_FIELDS}
    else:
        user_inputs = {field.name: value for field, value in zip(USER_FIELDS, user_values, strict=True)}

    try:
        forecast = ForecastClient().fetch_forecast(float(user_inputs["HRSF"]))
        features = generate_features(forecast, user_inputs)
    except Exception as exc:  # noqa: BLE001
        advanced_updates = [gr.update() for _ in UI_FIELDS]
        display_updates = [gr.update() for _ in AUTO_FIELDS]
        return [*advanced_updates, *display_updates, auto_state, f"Auto-fill failed: {exc}"]

    features["year"] = FIXED_YEAR
    advanced_updates = [gr.update(value=features[field.name]) for field in UI_FIELDS]
    display_updates = [
        gr.update(value=_display_text(field, features[field.name])) for field in AUTO_FIELDS
    ]
    return [
        *advanced_updates,
        *display_updates,
        features,
        "Auto-fill complete for NYC forecast.",
    ]


def _toggle_mode(is_advanced: bool, auto_state: dict[str, object], *values):
    user_values = values[: len(USER_FIELDS)]
    advanced_values = values[len(USER_FIELDS) :]

    if is_advanced:
        advanced_data = {
            field.name: value for field, value in zip(UI_FIELDS, advanced_values, strict=True)
        }
        basic_updates = [
            gr.update(value=advanced_data[field.name]) for field in USER_FIELDS
        ]
        display_updates = [
            gr.update(value=_display_text(field, advanced_data[field.name]))
            for field in AUTO_FIELDS
        ]
        advanced_updates = [gr.update() for _ in UI_FIELDS]
        mode_update = False
        auto_state_update = advanced_data
        return [
            mode_update,
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(value="Edit all values"),
            *basic_updates,
            *advanced_updates,
            *display_updates,
            auto_state_update,
        ]

    user_inputs = {field.name: value for field, value in zip(USER_FIELDS, user_values, strict=True)}
    data = build_default_input()
    if auto_state:
        data.update(auto_state)
    data.update(user_inputs)
    data["year"] = FIXED_YEAR

    advanced_updates = [gr.update(value=data[field.name]) for field in UI_FIELDS]
    basic_updates = [gr.update() for _ in USER_FIELDS]
    display_updates = [
        gr.update(value=_display_text(field, data[field.name])) for field in AUTO_FIELDS
    ]
    return [
        True,
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(value="Use auto-filled view"),
        *basic_updates,
        *advanced_updates,
        *display_updates,
        data,
    ]


def build_ui() -> gr.Blocks:
    with gr.Blocks() as demo:
        gr.Markdown("# Fishing Catch Predictor")
        gr.Markdown("Enter trip and conditions data to get a catch prediction.")
        is_advanced = gr.State(False)
        auto_state = gr.State(build_default_input())

        with gr.Row():
            with gr.Column(visible=True) as basic_column:
                gr.Markdown("## Trip inputs")
                basic_user_inputs: list[Component] = []
                for field in USER_FIELDS:
                    basic_user_inputs.append(_component_for_field(field, interactive=True))

            with gr.Column(visible=False) as advanced_column:
                gr.Markdown("## Edit all values")
                advanced_inputs = build_input_components()

        with gr.Column(visible=True) as auto_display_column:
            gr.Markdown("## Auto-filled values")
            default_values = build_default_input()
            auto_display = [
                gr.Markdown(value=_display_text(field, default_values[field.name]))
                for field in AUTO_FIELDS
            ]

        toggle_button = gr.Button("Edit all values")
        toggle_button.click(
            fn=_toggle_mode,
            inputs=[is_advanced, auto_state, *basic_user_inputs, *advanced_inputs],
            outputs=[
                is_advanced,
                basic_column,
                advanced_column,
                auto_display_column,
                toggle_button,
                *basic_user_inputs,
                *advanced_inputs,
                *auto_display,
                auto_state,
            ],
        )

        auto_fill_status = gr.Textbox(
            label="Auto-fill status",
            value="Auto-fill not completed for NYC forecast.",
            interactive=False,
        )
        auto_fill_button = gr.Button("Auto-fill NYC forecast")
        auto_fill_button.click(
            fn=_auto_fill,
            inputs=[is_advanced, auto_state, *basic_user_inputs, *advanced_inputs],
            outputs=[*advanced_inputs, *auto_display, auto_state, auto_fill_status],
        )

        output = gr.Textbox(label="Prediction", interactive=False)
        predict_button = gr.Button("Predict")
        predict_button.click(
            fn=_predict,
            inputs=[is_advanced, auto_state, *basic_user_inputs, *advanced_inputs],
            outputs=output,
        )

    return demo


demo = build_ui()


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
