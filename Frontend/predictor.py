from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from schema import SCHEMA, validate_input

from huggingface_hub import hf_hub_download


MODEL_REPO = os.getenv("HF_MODEL_REPO", "RossNeyman/fishing-catch-model")
MODEL_FILENAME = os.getenv("HF_MODEL_FILENAME", "stacking_classifier.joblib")

MODEL_PATH = Path(
    hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILENAME)
)

@lru_cache(maxsize=1)
def load_model() -> Any:
    return joblib.load(MODEL_PATH)


def _to_numeric(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    return float(value)


def build_feature_vector(data: dict[str, Any]) -> np.ndarray:
    values = [_to_numeric(data[field.name]) for field in SCHEMA]
    return np.array([values], dtype=float)


def predict_from_dict(data: dict[str, Any]) -> tuple[Any, float | None]:
    validate_input(data)
    model = load_model()
    features = build_feature_vector(data)
    label = model.predict(features)[0]

    probability: float | None = None
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(features)[0]
        if hasattr(model, "classes_"):
            classes = list(model.classes_)
            if label in classes:
                probability = float(proba[classes.index(label)])
            else:
                probability = float(max(proba))
        else:
            probability = float(max(proba))

    return label, probability


def predict_from_values(*values: object) -> tuple[Any, float | None]:
    data = {field.name: value for field, value in zip(SCHEMA, values, strict=True)}
    return predict_from_dict(data)
