# %% [markdown]
# # Total Catch Classification - Stacking Pipeline
#
# **Architecture:**
# 1. Single-model baselines (RF, XGB, LightGBM)
# 2. Stacking Classifier (RF + LightGBM + XGB -> Logistic Regression meta)
#
# Binary target: `has_catch` (1 if `total_catch` > 0).

# %% Cell 1 - Imports
import joblib
import pandas as pd
import numpy as np
import warnings
from typing import cast

from sklearn.model_selection import (
    train_test_split,
    StratifiedKFold,
    cross_validate,
    cross_val_predict,
)
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.base import BaseEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    f1_score,
    precision_recall_fscore_support,
)
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

warnings.filterwarnings("ignore", category=UserWarning)


RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

# %% Cell 2 - Data Loading (Pre-engineered Dataset)
df = pd.read_csv("data/processed/df_tripdata_engineered_with_total.csv")
print(f"Dataset shape: {df.shape}")

if "total_catch" in df.columns:
    print(
        f"Target stats - mean: {df['total_catch'].mean():.2f}, "
        f"median: {df['total_catch'].median():.1f}, "
        f"max: {df['total_catch'].max():.0f}, "
        f"zeros: {(df['total_catch'] == 0).mean():.1%}"
    )

if "has_catch" not in df.columns:
    if "total_catch" not in df.columns:
        raise ValueError("Expected 'has_catch' or 'total_catch' in the dataset.")
    df["has_catch"] = (df["total_catch"] > 0).astype(int)

feature_cols = [c for c in df.columns if c not in {"has_catch", "total_catch"}]
print(f"Final features: {len(feature_cols)} columns")

# %% Cell 3 - Train/Test Split
X = df[feature_cols].copy()
y = df["has_catch"].copy()

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=RANDOM_STATE,
    stratify=y,
)

print(f"Train: {X_train.shape[0]:,} rows | Test: {X_test.shape[0]:,} rows")
print(
    f"Train catch rate: {y_train.mean():.1%} | Test catch rate: {y_test.mean():.1%}"
)

# %% Cell 4 - Models and Cross-Validation
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
scoring = {
    "accuracy": "accuracy",
    "precision": "precision",
    "recall": "recall",
    "f1": "f1",
}

rf_clf = RandomForestClassifier(
    n_estimators=300,
    n_jobs=-1,
    random_state=RANDOM_STATE,
    class_weight="balanced",
)

lgbm_clf = LGBMClassifier(
    n_estimators=500,
    max_depth=8,
    learning_rate=0.05,
    n_jobs=-1,
    random_state=RANDOM_STATE,
    verbose=-1,
    is_unbalance=True,
)

xgb_clf = XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    tree_method="hist",
    n_jobs=-1,
    random_state=RANDOM_STATE,
    eval_metric="logloss",
)

stack_estimators = cast(
    list[tuple[str, BaseEstimator]],
    [("rf", rf_clf), ("lgbm", lgbm_clf), ("xgb", xgb_clf)],
)

stack_clf = StackingClassifier(
    estimators=stack_estimators,
    final_estimator=LogisticRegression(max_iter=2000, class_weight="balanced"),
    cv=cv,
    stack_method="predict_proba",
    n_jobs=1,
    passthrough=False,
)

models = {
    "Random Forest": rf_clf,
    "LightGBM": lgbm_clf,
    "XGBoost": xgb_clf,
    "Stacking Classifier": stack_clf,
}


def summarize_cv_scores(name: str, results):
    metrics = {}
    print(f"\n{name} - 5-fold CV (train only)")
    for metric in ["accuracy", "precision", "recall", "f1"]:
        values = results[f"test_{metric}"]
        metrics[metric] = (values.mean(), values.std())
        print(f"  {metric}: {values.mean():.4f} +/- {values.std():.4f}")
    return metrics


cv_summary = {}
print("\nCross-validating models on the training set only...")
for name, model in models.items():
    results = cross_validate(
        model,
        X_train,
        y_train,
        cv=cv,
        scoring=scoring,
        n_jobs=1,
    )
    cv_summary[name] = summarize_cv_scores(name, results)


def find_best_threshold(y_true, probas):
    thresholds = np.linspace(0.05, 0.95, 91)
    best_t = 0.5
    best_f1 = -1.0
    for t in thresholds:
        preds = (probas >= t).astype(int)
        score = f1_score(y_true, preds, zero_division=0)
        if score > best_f1:
            best_f1 = score
            best_t = t
    return best_t, best_f1


thresholds = {}
print("\nTuning thresholds on training set (out-of-fold probabilities)...")
for name, model in models.items():
    oof_proba = cross_val_predict(
        model,
        X_train,
        y_train,
        cv=cv,
        method="predict_proba",
        n_jobs=1,
    )[:, 1]
    best_t, best_f1 = find_best_threshold(y_train, oof_proba)
    thresholds[name] = best_t
    print(f"  {name}: threshold={best_t:.2f}, OOF F1={best_f1:.4f}")

# %% Cell 5 - Fit on Training Set and Evaluate on Held-Out Test
test_summary = {}


def evaluate_on_test(name: str, model, threshold: float, show_details: bool = False):
    model.fit(X_train, y_train)
    probas = model.predict_proba(X_test)[:, 1]
    preds = (probas >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test,
        preds,
        average="binary",
        zero_division=0,
    )
    accuracy = accuracy_score(y_test, preds)

    print(f"\n{name} - Held-out test set")
    print(f"  Threshold: {threshold:.2f}")
    print(f"  Accuracy:  {accuracy:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1:        {f1:.4f}")

    if show_details:
        print("\nClassification report:")
        print(classification_report(y_test, preds))
        print("Confusion matrix:")
        print(confusion_matrix(y_test, preds))

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


for name, model in models.items():
    show_details = name == "Stacking Classifier"
    test_summary[name] = evaluate_on_test(
        name,
        model,
        threshold=thresholds[name],
        show_details=show_details,
    )

# %% Cell 6 - Recommendation and Model Save
cv_best = max(cv_summary, key=lambda m: cv_summary[m]["f1"][0])
test_best = max(test_summary, key=lambda m: test_summary[m]["f1"])

print("\nRecommendation")
if cv_best == "Stacking Classifier" and test_best == "Stacking Classifier":
    print("Stacking Classifier is best on CV F1 and held-out test F1.")
else:
    print(
        "Stacking Classifier is not best on both CV and test F1. "
        f"Best CV: {cv_best}. Best test: {test_best}."
    )

joblib.dump(stack_clf, "stacking_classifier.joblib")
print("\nSaved model: stacking_classifier.joblib")
