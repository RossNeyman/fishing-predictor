# Frontend Tool Strict Task Checklist

## Rules
1. Execute only the first incomplete task (top to bottom).
2. Do not skip, reorder, or bundle future tasks.
3. Keep implementations utilitarian and production-safe.
4. Every task must include tests and passing evidence.
5. Use context.md and agent-instructions.md before writing code.

## Tasks

- [ ] T01 Define required input schema for inference
	- Deliverables: input field list, types, ranges, and defaults aligned to model expectations.
	- Exit criteria: schema matches model features and is documented in context.md.
	- Required tests: schema validation unit tests.

- [ ] T02 Implement Gradio UI layout and input widgets
	- Deliverables: Gradio Blocks layout and all input widgets wired to schema.
	- Exit criteria: UI renders locally with all inputs present and labeled.
	- Required tests: UI smoke test (render without error).

- [ ] T03 Implement prediction handler and model loading
	- Deliverables: model loader with caching and prediction function.
	- Exit criteria: handler returns class label and probability for sample input.
	- Required tests: prediction unit test with mocked model.

- [ ] T04 Add validation and user-friendly output formatting
	- Deliverables: input validation, error messaging, and formatted output.
	- Exit criteria: invalid inputs surface clear errors; valid inputs produce readable result.
	- Required tests: validation unit tests for pass/fail cases.

- [ ] T05 Add tests for inference and UI behavior
	- Deliverables: end-to-end inference test and UI behavior tests.
	- Exit criteria: tests run from a single command and pass.
	- Required tests: inference integration test; UI behavior test.

- [ ] T06 Add Space entry point and run instructions
	- Deliverables: Hugging Face Space entrypoint and README with run steps.
	- Exit criteria: app launches on Spaces with documented setup.
	- Required tests: entrypoint import smoke test.

## Completion Log
- Add one line per finished task: `YYYY-MM-DD | Task ID | Agent | Result | Test Summary`
