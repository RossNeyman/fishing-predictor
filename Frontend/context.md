# Frontend Context

This folder will host a simple Gradio UI intended for Hugging Face Spaces. The UI will collect user inputs needed to run inference using the model at ../model/stacking_classifier.joblib to predict whether a user will catch fish based on weather conditions and planned fishing details.

## Components Overview (planned)
- Inference UI: Gradio interface with input widgets for weather conditions and fishing plan details (exact fields TBD). Collects user inputs and triggers prediction.
- Prediction Handler: Loads the model, performs feature preprocessing (if required), runs inference, and returns a clear result message.
- Validation/Defaults: Ensures required inputs are provided and supplies safe defaults where appropriate.
- Outputs: A human-readable prediction result and, if needed, a probability score.

## Constraints
- Target deployment: Hugging Face Spaces.
- UI framework: Gradio.
- Model file: ../model/stacking_classifier.joblib.
