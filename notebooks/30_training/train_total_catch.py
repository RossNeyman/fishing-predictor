
# %% [markdown]
# # 🎣 Total Catch Prediction — Stacking Pipeline
#
# **Architecture:**
# 1. Single-model baselines (RF, GBM, HGBM, XGB)
# 2. **Stacking Regressor** (RF + HGBM + GBM → XGB meta)
# 3. **Two-Stage Stacking** (Stacking Classifier gate + Stacking Regressor)
#
# All models use `log1p(total_catch)` as target to handle the skewed distribution.

# %% Cell 1 — Imports
import pandas as pd
import numpy as np
import warnings
import matplotlib.pyplot as plt

from sklearn.model_selection import (
    train_test_split, cross_val_score, KFold, StratifiedKFold,
)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import (
    RandomForestRegressor, RandomForestClassifier,
    GradientBoostingRegressor, GradientBoostingClassifier,
    HistGradientBoostingRegressor, HistGradientBoostingClassifier,
    StackingRegressor, StackingClassifier,
)
from sklearn.linear_model import Ridge
from sklearn.metrics import (
    mean_squared_error, r2_score, mean_absolute_error,
    classification_report, f1_score,
)
from xgboost import XGBRegressor, XGBClassifier

warnings.filterwarnings("ignore", category=UserWarning)
pd.set_option("display.max_columns", 40)

RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

# %% Cell 2 — Data Loading & Feature Engineering
df = pd.read_csv("../data/processed/df_tripdata_engineered_with_total.csv")
print(f"Dataset shape: {df.shape}")
print(f"Target stats — mean: {df['total_catch'].mean():.2f}, "
      f"median: {df['total_catch'].median():.1f}, "
      f"max: {df['total_catch'].max():.0f}, "
      f"zeros: {(df['total_catch'] == 0).mean():.1%}")

# --- Temporal features ---
ts = pd.to_datetime(df["SURVEY_TIMESTAMP"])
df["year"]       = ts.dt.year
df["month"]      = ts.dt.month
df["day"]        = ts.dt.day
df["hour"]       = ts.dt.hour
df["dayofweek"]  = ts.dt.dayofweek
df["is_weekend"] = df["dayofweek"].isin([5, 6]).astype(int)

# Cyclical encoding for periodic features (hour, month, dayofweek)
for col, period in [("hour", 24), ("month", 12), ("dayofweek", 7)]:
    df[f"{col}_sin"] = np.sin(2 * np.pi * df[col] / period)
    df[f"{col}_cos"] = np.cos(2 * np.pi * df[col] / period)

# --- Interaction features ---
df["temp_diff"]       = df["avg_air_temp_c"] - df["avg_water_temp_c"]
df["wind_x_pressure"] = df["avg_wind_speed"] * df["avg_air_pressure"]
df["gust_ratio"]      = df["avg_wind_gust"] / (df["avg_wind_speed"] + 1e-6)

# --- One-hot encode KOD ---
df = pd.get_dummies(df, columns=["KOD"], drop_first=True)

# --- Drop non-feature columns ---
df = df.drop(columns=["ID_CODE", "SURVEY_TIMESTAMP"])

print(f"Final features: {df.shape[1] - 1} columns")
df.head()

# %% Cell 3 — Train/Test Split & Target Transformation
# Binary target for the classifier gate
df["has_catch"] = (df["total_catch"] > 0).astype(int)

# Features
feature_cols = [c for c in df.columns if c not in ["total_catch", "has_catch"]]
X = df[feature_cols].copy()
y_reg   = df["total_catch"].copy()
y_class = df["has_catch"].copy()

# Log-transform the regression target (handles skew + zeros)
y_log = np.log1p(y_reg)

# Split — keep indices aligned for both tasks
X_train, X_test, y_log_train, y_log_test, y_class_train, y_class_test, y_reg_train, y_reg_test = \
    train_test_split(X, y_log, y_class, y_reg, test_size=0.2, random_state=RANDOM_STATE)

print(f"Train: {X_train.shape[0]:,} rows | Test: {X_test.shape[0]:,} rows")
print(f"Train catch rate: {y_class_train.mean():.1%} | Test catch rate: {y_class_test.mean():.1%}")


# %% Cell 4 — Helper: Evaluation Function
def evaluate(name: str, y_true_log, y_pred_log, y_true_raw=None):
    """Evaluate a model on log-scale and original scale."""
    # Predictions back to original scale
    y_pred_raw = np.expm1(np.clip(y_pred_log, 0, None))
    if y_true_raw is None:
        y_true_raw = np.expm1(y_true_log)

    rmse_log = np.sqrt(mean_squared_error(y_true_log, y_pred_log))
    rmse_raw = np.sqrt(mean_squared_error(y_true_raw, y_pred_raw))
    r2       = r2_score(y_true_raw, y_pred_raw)
    mae      = mean_absolute_error(y_true_raw, y_pred_raw)

    print(f"\n{'='*55}")
    print(f"  {name}")
    print(f"{'='*55}")
    print(f"  RMSE (log):     {rmse_log:.4f}")
    print(f"  RMSE (raw):     {rmse_raw:.2f}")
    print(f"  MAE  (raw):     {mae:.2f}")
    print(f"  R²   (raw):     {r2:.4f}")
    return {"model": name, "rmse_log": rmse_log, "rmse_raw": rmse_raw, "mae": mae, "r2": r2}


# %% Cell 5 — Individual Model Baselines
results = []

# --- 5a. Ridge (baseline) ---
ridge = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=1.0))])
ridge.fit(X_train, y_log_train)
results.append(evaluate("Ridge (baseline)", y_log_test, ridge.predict(X_test), y_reg_test))

# --- 5b. Random Forest ---
rf = RandomForestRegressor(
    n_estimators=500, max_depth=20, min_samples_leaf=4,
    n_jobs=-1, random_state=RANDOM_STATE,
)
rf.fit(X_train, y_log_train)
results.append(evaluate("Random Forest", y_log_test, rf.predict(X_test), y_reg_test))

# --- 5c. Gradient Boosting ---
gbm = GradientBoostingRegressor(
    n_estimators=300, max_depth=5, learning_rate=0.1,
    subsample=0.8, random_state=RANDOM_STATE,
)
gbm.fit(X_train, y_log_train)
results.append(evaluate("Gradient Boosting", y_log_test, gbm.predict(X_test), y_reg_test))

# --- 5d. HistGradientBoosting ---
hgbm = HistGradientBoostingRegressor(
    max_iter=500, max_depth=8, learning_rate=0.05,
    random_state=RANDOM_STATE,
    early_stopping=True, validation_fraction=0.1, n_iter_no_change=20,
)
hgbm.fit(X_train, y_log_train)
results.append(evaluate("HistGradientBoosting", y_log_test, hgbm.predict(X_test), y_reg_test))

# --- 5e. XGBoost ---
xgb = XGBRegressor(
    n_estimators=500, max_depth=6, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8,
    tree_method="hist", n_jobs=-1, random_state=RANDOM_STATE,
    eval_metric="rmse",
)
xgb.fit(X_train, y_log_train)
results.append(evaluate("XGBoost", y_log_test, xgb.predict(X_test), y_reg_test))

print("\n\n" + "="*60)
print("  BASELINES SUMMARY")
print("="*60)
results_df = pd.DataFrame(results).sort_values("r2", ascending=False)
print(results_df.to_string(index=False))


# %% Cell 6 — Stacking Regressor (RF + HGBM + GBM → XGB meta)
print("\n🔧 Training Stacking Regressor...")

base_estimators = [
    ("rf", RandomForestRegressor(
        n_estimators=300, max_depth=20, min_samples_leaf=4,
        n_jobs=-1, random_state=RANDOM_STATE,
    )),
    ("hgbm", HistGradientBoostingRegressor(
        max_iter=500, max_depth=8, learning_rate=0.05,
        random_state=RANDOM_STATE,
        early_stopping=True, validation_fraction=0.1, n_iter_no_change=20,
    )),
    ("gbm", GradientBoostingRegressor(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        subsample=0.8, random_state=RANDOM_STATE,
    )),
]

meta_regressor = XGBRegressor(
    n_estimators=300, max_depth=4, learning_rate=0.05,
    tree_method="hist", n_jobs=-1, random_state=RANDOM_STATE,
    eval_metric="rmse",
)

stack_reg = StackingRegressor(
    estimators=base_estimators,
    final_estimator=meta_regressor,
    cv=KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE),
    n_jobs=1,           # XGB meta already uses all cores
    passthrough=True,   # meta sees original features too
)

stack_reg.fit(X_train, y_log_train)
results.append(evaluate(
    "⭐ Stacking Regressor", y_log_test, stack_reg.predict(X_test), y_reg_test
))


# %% Cell 7 — Two-Stage Stacking (Classifier Gate + Stacking Regressor)
# Stage 1: Stacking Classifier — "will there be a catch?"
print("\n🔧 Training Two-Stage Stacking...")
print("  Stage 1: Stacking Classifier (catch / no-catch gate)...")

clf_base = [
    ("rf", RandomForestClassifier(
        n_estimators=300, n_jobs=-1, random_state=RANDOM_STATE,
        class_weight="balanced",
    )),
    ("hgbm", HistGradientBoostingClassifier(
        max_iter=500, learning_rate=0.05, random_state=RANDOM_STATE,
        early_stopping=True, validation_fraction=0.1, n_iter_no_change=20,
    )),
    ("gbm", GradientBoostingClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        random_state=RANDOM_STATE,
    )),
]

clf_meta = XGBClassifier(
    n_estimators=300, max_depth=4, learning_rate=0.05,
    tree_method="hist", n_jobs=-1, random_state=RANDOM_STATE,
    eval_metric="logloss",
)

stack_clf = StackingClassifier(
    estimators=clf_base,
    final_estimator=clf_meta,
    cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE),
    stack_method="predict_proba",
    n_jobs=1,
    passthrough=True,
)

stack_clf.fit(X_train, y_class_train)

# Evaluate classifier
clf_preds = stack_clf.predict(X_test)
print("\n  Classification Gate Report:")
print(classification_report(y_class_test, clf_preds))

# Stage 2: Stacking Regressor — "how much?" (trained only on catch > 0)
print("  Stage 2: Stacking Regressor (amount, trained on catch > 0)...")

mask_catch = y_reg_train > 0
X_train_catch = X_train[mask_catch]
y_log_train_catch = y_log_train[mask_catch]

# Reuse same architecture as Cell 6 but re-trained on catch-only data
reg_base = [
    ("rf", RandomForestRegressor(
        n_estimators=300, max_depth=20, min_samples_leaf=4,
        n_jobs=-1, random_state=RANDOM_STATE,
    )),
    ("hgbm", HistGradientBoostingRegressor(
        max_iter=500, max_depth=8, learning_rate=0.05,
        random_state=RANDOM_STATE,
        early_stopping=True, validation_fraction=0.1, n_iter_no_change=20,
    )),
    ("gbm", GradientBoostingRegressor(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        subsample=0.8, random_state=RANDOM_STATE,
    )),
]

reg_meta = XGBRegressor(
    n_estimators=300, max_depth=4, learning_rate=0.05,
    tree_method="hist", n_jobs=-1, random_state=RANDOM_STATE,
    eval_metric="rmse",
)

stack_reg_s2 = StackingRegressor(
    estimators=reg_base,
    final_estimator=reg_meta,
    cv=KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE),
    n_jobs=1,
    passthrough=True,
)

stack_reg_s2.fit(X_train_catch, y_log_train_catch)

# Combine: classifier gate × regressor amount
probs = stack_clf.predict_proba(X_test)[:, 1]

# Sweep thresholds to find optimal
best_r2, best_thresh = -np.inf, 0.5
for t in np.arange(0.3, 0.7, 0.05):
    gate = (probs > t).astype(int)
    reg_pred_log = stack_reg_s2.predict(X_test)
    combined_log = np.where(gate == 1, reg_pred_log, 0)
    combined_raw = np.expm1(np.clip(combined_log, 0, None))
    r2_t = r2_score(y_reg_test, combined_raw)
    if r2_t > best_r2:
        best_r2, best_thresh = r2_t, t

print(f"\n  Optimal classifier threshold: {best_thresh:.2f}")

gate = (probs > best_thresh).astype(int)
reg_pred_log = stack_reg_s2.predict(X_test)
final_log = np.where(gate == 1, reg_pred_log, 0)

results.append(evaluate(
    "⭐ Two-Stage Stacking", y_log_test, final_log, y_reg_test
))


# %% Cell 8 — Final Comparison
print("\n\n" + "="*60)
print("  FINAL MODEL COMPARISON")
print("="*60)
results_df = pd.DataFrame(results).sort_values("r2", ascending=False)
print(results_df.to_string(index=False))

# Bar chart
fig, axes = plt.subplots(1, 3, figsize=(16, 5))

for ax, metric, title in zip(axes,
    ["r2", "rmse_raw", "mae"],
    ["R² (higher = better)", "RMSE (lower = better)", "MAE (lower = better)"]):
    colors = ["#2ecc71" if "Stacking" in m else "#3498db" if m != "Ridge (baseline)" else "#95a5a6"
              for m in results_df["model"]]
    ax.barh(results_df["model"], results_df[metric], color=colors)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.invert_yaxis()

plt.tight_layout()
plt.savefig("model_comparison.png", dpi=150, bbox_inches="tight")
plt.show()
print("\n✅ Chart saved: model_comparison.png")


# %% Cell 9 — Feature Importance (from best stacking base models)
print("\n📊 Feature Importance (from RF base learner in stacking):")

# Get RF from the stacking regressor
rf_in_stack = stack_reg.named_estimators_["rf"]
importances = pd.Series(rf_in_stack.feature_importances_, index=feature_cols)
top20 = importances.sort_values(ascending=False).head(20)

fig, ax = plt.subplots(figsize=(10, 7))
top20.sort_values().plot.barh(ax=ax, color="#2ecc71")
ax.set_title("Top 20 Feature Importances (RF in Stack)", fontsize=14, fontweight="bold")
ax.set_xlabel("Importance")
plt.tight_layout()
plt.savefig("feature_importance.png", dpi=150, bbox_inches="tight")
plt.show()
print("✅ Chart saved: feature_importance.png")


# %% Cell 10 — Cross-Validation of Best Model
print("\n🔄 5-Fold Cross-Validation of Stacking Regressor...")

cv_scores = cross_val_score(
    stack_reg, X, y_log,
    cv=KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE),
    scoring="r2", n_jobs=1,
)
print(f"  R² per fold: {cv_scores}")
print(f"  Mean R²:     {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

cv_rmse = cross_val_score(
    stack_reg, X, y_log,
    cv=KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE),
    scoring="neg_root_mean_squared_error", n_jobs=1,
)
print(f"  RMSE per fold: {-cv_rmse}")
print(f"  Mean RMSE:     {-cv_rmse.mean():.4f} ± {cv_rmse.std():.4f}")

print("\n✅ Pipeline complete!")

# PS C:\Users\ross9\Documents\GitHub\fishing-predictor\notebooks> py train_total_catch.py
# Dataset shape: (70862, 32)
# Target stats — mean: 6.14, median: 1.0, max: 669, zeros: 42.0%
# Final features: 44 columns
# Train: 56,689 rows | Test: 14,173 rows
# Train catch rate: 57.9% | Test catch rate: 58.6%

# =======================================================
#   Ridge (baseline)
# =======================================================
#   RMSE (log):     1.1274
#   RMSE (raw):     14.70
#   MAE  (raw):     5.84
#   R²   (raw):     -0.0355

# =======================================================
#   Random Forest
# =======================================================
#   RMSE (log):     0.9043
#   RMSE (raw):     13.37
#   MAE  (raw):     4.82
#   R²   (raw):     0.1426

# =======================================================
#   Gradient Boosting
# =======================================================
#   RMSE (log):     0.9800
#   RMSE (raw):     13.83
#   MAE  (raw):     5.22
#   R²   (raw):     0.0831

# =======================================================
#   HistGradientBoosting
# =======================================================
#   RMSE (log):     0.9712
#   RMSE (raw):     13.79
#   MAE  (raw):     5.18
#   R²   (raw):     0.0881

# =======================================================
#   XGBoost
# =======================================================
#   RMSE (log):     0.9497
#   RMSE (raw):     13.62
#   MAE  (raw):     5.07
#   R²   (raw):     0.1110


# ============================================================
#   BASELINES SUMMARY
# ============================================================
#                model  rmse_log  rmse_raw      mae        r2
#        Random Forest  0.904331 13.374844 4.823740  0.142583
#              XGBoost  0.949721 13.618667 5.068110  0.111037
# HistGradientBoosting  0.971208 13.792935 5.175800  0.088140
#    Gradient Boosting  0.980034 13.831139 5.215222  0.083082
#     Ridge (baseline)  1.127392 14.698238 5.840484 -0.035488

# 🔧 Training Stacking Regressor...

# =======================================================
#   ⭐ Stacking Regressor
# =======================================================
#   RMSE (log):     0.8809
#   RMSE (raw):     12.84
#   MAE  (raw):     4.54
#   R²   (raw):     0.2093

# 🔧 Training Two-Stage Stacking...
#   Stage 1: Stacking Classifier (catch / no-catch gate)...

#   Classification Gate Report:
#               precision    recall  f1-score   support

#            0       0.78      0.72      0.75      5872
#            1       0.81      0.85      0.83      8301

#     accuracy                           0.80     14173
#    macro avg       0.79      0.79      0.79     14173
# weighted avg       0.80      0.80      0.80     14173

#   Stage 2: Stacking Regressor (amount, trained on catch > 0)...

#   Optimal classifier threshold: 0.50

# =======================================================
#   ⭐ Two-Stage Stacking
# =======================================================
#   RMSE (log):     0.9266
#   RMSE (raw):     11.99
#   MAE  (raw):     4.29
#   R²   (raw):     0.3110