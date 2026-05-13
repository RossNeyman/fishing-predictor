# Frontend Tool Strict Task Checklist

## Rules
1. Execute only the first incomplete task (top to bottom).
2. Do not skip, reorder, or bundle future tasks.
3. Keep implementations utilitarian and production-safe.
4. Every task must include tests and passing evidence.
5. Use context.md and agent-instructions.md before writing code.

## Tasks

- [x] T01 Define required input schema for inference
	- Deliverables: input field list, types, ranges, and defaults aligned to model expectations.
	- Exit criteria: schema matches model features and is documented in context.md.
	- Required tests: schema validation unit tests.

- [x] T02 Implement Gradio UI layout and input widgets
	- Deliverables: Gradio Blocks layout and all input widgets wired to schema.
	- Exit criteria: UI renders locally with all inputs present and labeled.
	- Required tests: UI smoke test (render without error).

- [x] T03 Implement prediction handler and model loading
	- Deliverables: model loader with caching and prediction function.
	- Exit criteria: handler returns class label and probability for sample input.
	- Required tests: prediction unit test with mocked model.

- [x] T04 Add validation and user-friendly output formatting
	- Deliverables: input validation, error messaging, and formatted output.
	- Exit criteria: invalid inputs surface clear errors; valid inputs produce readable result.
	- Required tests: validation unit tests for pass/fail cases.

- [x] T05 Add tests for inference and UI behavior
	- Deliverables: end-to-end inference test and UI behavior tests.
	- Exit criteria: tests run from a single command and pass.
	- Required tests: inference integration test; UI behavior test.

- [x] T06 Add Space entry point and run instructions
	- Deliverables: Hugging Face Space entrypoint and README with run steps.
	- Exit criteria: app launches on Spaces with documented setup.
	- Required tests: entrypoint import smoke test.

- [x] T07 Plan NYC live weather auto-fill inputs
	- Deliverables: documented list of which inputs are user-supplied vs auto-filled, including exclusions for FFDAYS2, HRSF, MODE_F, CNTRBTRS, and removal of IMP_REC from the form.
	- Exit criteria: plan captured in context.md and referenced in implementation notes.
	- Required tests: documentation-only (no tests).

- [x] T08 Implement NYC forecast fetcher
	- Deliverables: data client that pulls NYC-area forecast for the upcoming HRSF window; configurable provider and API key handling.
	- Exit criteria: fetcher returns normalized forecast data needed for feature engineering.
	- Required tests: mocked API unit test for success/failure paths.

- [x] T09 Build forward-looking feature engineering pipeline
	- Deliverables: feature generator that computes all engineered features from forecast data for the upcoming HRSF window; IMP_REC forced to 0; uses forward-looking windows only.
	- Exit criteria: generated feature dict matches model schema and uses forecast-only data.
	- Required tests: deterministic unit tests for feature calculations with fixture data.

- [x] T10 Integrate auto-fill into UI flow
	- Deliverables: UI controls to input HRSF and trigger auto-fill for NYC; auto-filled fields locked or clearly labeled; IMP_REC removed from form.
	- Exit criteria: end-to-end UI fills all required fields except FFDAYS2, HRSF, MODE_F, CNTRBTRS.
	- Required tests: UI behavior test verifying auto-fill population.

- [x] T11 Add end-to-end auto-fill inference test
	- Deliverables: integration test that fetches mocked forecast, generates features, and runs prediction.
	- Exit criteria: inference succeeds with auto-filled inputs and returns label/probability.
	- Required tests: integration test with mocked forecast client.

- [x] T12 Add auto-filled display toggle
	- Deliverables: default UI shows user inputs plus auto-filled display; toggle button enables full edit mode.
	- Exit criteria: auto-fill updates the display and advanced inputs; prediction works in both modes.
	- Required tests: UI behavior test updates for auto-fill outputs.

- [x] T13 Customize input display labels
	- Deliverables: user-facing labels for FFDAYS2, HRSF, MODE_F, and CNTRBTRS without changing functionality.
	- Exit criteria: updated labels render in basic and advanced views.
	- Required tests: UI label expectations updated.

- [x] T14 Add default auto-fill status message
	- Deliverables: auto-fill status shows a default message on page load.
	- Exit criteria: status text indicates NYC forecast needs auto-fill until run.
	- Required tests: UI config test for default status value.

- [x] T15 Hide year input
	- Deliverables: year removed from UI and forced to 2024 for predictions.
	- Exit criteria: year not visible in basic or advanced views; predictions still validate.
	- Required tests: UI test ensuring year is excluded from UI fields.

## Completion Log
- Add one line per finished task: `YYYY-MM-DD | Task ID | Agent | Result | Test Summary`
- 2026-05-12 | T01 | GitHub Copilot | Completed | python -m unittest discover -s Frontend/tests
- 2026-05-12 | T02 | GitHub Copilot | Completed | python -m unittest discover -s Frontend/tests
- 2026-05-12 | T03 | GitHub Copilot | Completed | python -m unittest discover -s Frontend/tests
- 2026-05-12 | T04 | GitHub Copilot | Completed | python -m unittest discover -s Frontend/tests
- 2026-05-12 | T05 | GitHub Copilot | Completed | python -m unittest discover -s Frontend/tests
- 2026-05-12 | T06 | GitHub Copilot | Completed | python -m unittest discover -s Frontend
- 2026-05-12 | T07 | GitHub Copilot | Completed | python -m unittest discover -s Frontend/tests
- 2026-05-12 | T08 | GitHub Copilot | Completed | python -m unittest discover -s Frontend/tests
- 2026-05-12 | T09 | GitHub Copilot | Completed | python -m unittest discover -s Frontend/tests
- 2026-05-12 | T10 | GitHub Copilot | Completed | python -m unittest discover -s Frontend/tests
- 2026-05-12 | T11 | GitHub Copilot | Completed | python -m unittest discover -s Frontend/tests
- 2026-05-13 | T12 | GitHub Copilot | Completed | python -m unittest discover -s Frontend/tests
- 2026-05-13 | T13 | GitHub Copilot | Completed | python -m unittest discover -s Frontend/tests
- 2026-05-13 | T14 | GitHub Copilot | Completed | python -m unittest discover -s Frontend/tests
- 2026-05-13 | T15 | GitHub Copilot | Completed | python -m unittest discover -s Frontend/tests
