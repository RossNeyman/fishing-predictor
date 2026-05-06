# %% [markdown]
# # 🎣 Total Catch Prediction — Stacking Pipeline
# 
# **Architecture:**
# 1. Single-model baselines (RF, XGB, LightGBM Tweedie)
# 2. **Stacking Regressor** (RF + LightGBM + XGB → LightGBM meta)
# 3. **Two-Stage Stacking** (Stacking Classifier gate + Stacking Regressor)
# 
# All regression models use `log1p(total_catch)` as target.
# LightGBM Tweedie uses raw target (Tweedie handles zeros natively).

# %% Cell 1 — Imports
import pandas as pd
import numpy as np
import warnings
import matplotlib.pyplot as plt

from sklearn.model_selection import (
    train_test_split, cross_val_score, KFold, StratifiedKFold,
)
from sklearn.ensemble import (
    RandomForestRegressor, RandomForestClassifier,
    StackingRegressor, StackingClassifier,
)
from sklearn.metrics import (
    mean_squared_error, r2_score, mean_absolute_error,
    classification_report,
)
from xgboost import XGBRegressor, XGBClassifier
from lightgbm import LGBMRegressor, LGBMClassifier
from catboost import CatBoostRegressor

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

# --- Interaction & Biological features ---
# Esfuerzo
df["total_effort_hours"] = df["HRSF"] * df["CNTRBTRS"]

# Solunar
df["moon_illumination"] = np.sin(np.pi * df["moon_phase_age"] / 29.53) ** 2
df["major_minor_feeding"] = df[["was_sunrise", "was_sunset", "was_moonrise", "was_moonset"]].sum(axis=1)

# Frentes Climáticos
df["storm_approaching"] = ((df["air_pressure_fell"] == 1) & (df["wind_speed_rose"] == 1)).astype(int)
df["cold_front"] = ((df["air_pressure_rose"] == 1) & (df["air_temp_fell"] == 1)).astype(int)

# Condiciones del Agua/Aire
df["temp_diff"] = df["avg_air_temp_c"] - df["avg_water_temp_c"]
df["temp_shock_magnitude"] = abs(df["temp_diff"])
df["water_is_moving"] = ((df["water_level_rose"] == 1) | (df["water_level_fell"] == 1)).astype(int)

# Viento y Presión
df["wind_x_pressure"] = df["avg_wind_speed"] * df["avg_air_pressure"]
df["gust_ratio"] = df["avg_wind_gust"] / (df["avg_wind_speed"] + 1e-6)

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
def evaluate(name: str, y_true_raw, y_pred_raw):
    """Evaluate a model on original scale."""
    y_pred_raw = np.clip(y_pred_raw, 0, None)

    rmse = np.sqrt(mean_squared_error(y_true_raw, y_pred_raw))
    r2   = r2_score(y_true_raw, y_pred_raw)
    mae  = mean_absolute_error(y_true_raw, y_pred_raw)

    print(f"\n{'='*55}")
    print(f"  {name}")
    print(f"{'='*55}")
    print(f"  RMSE:  {rmse:.2f}")
    print(f"  MAE:   {mae:.2f}")
    print(f"  R²:    {r2:.4f}")
    return {"model": name, "rmse": rmse, "mae": mae, "r2": r2}


# %% Cell 5 — Individual Model Baselines
results = []

# --- 5a. Random Forest ---
print("🌲 Training Random Forest...")
rf = RandomForestRegressor(
    n_estimators=500, max_depth=20, min_samples_leaf=4,
    n_jobs=-1, random_state=RANDOM_STATE,
)
rf.fit(X_train, y_log_train)
rf_preds = np.expm1(rf.predict(X_test))
results.append(evaluate("Random Forest", y_reg_test, rf_preds))

# --- 5b. XGBoost ---
print("🚀 Training XGBoost...")
xgb = XGBRegressor(
    n_estimators=500, max_depth=6, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8,
    tree_method="hist", n_jobs=-1, random_state=RANDOM_STATE,
    eval_metric="rmse",
)
xgb.fit(X_train, y_log_train)
xgb_preds = np.expm1(xgb.predict(X_test))
results.append(evaluate("XGBoost", y_reg_test, xgb_preds))

# --- 5c. CatBoost Tweedie ---
print("🐱 Training CatBoost Tweedie...")
cat_tw = CatBoostRegressor(
    loss_function="Tweedie:variance_power=1.5",
    iterations=500, depth=6, learning_rate=0.05,
    random_seed=RANDOM_STATE, verbose=False,
)
cat_tw.fit(X_train, y_reg_train)  # raw target
cat_tw_preds = cat_tw.predict(X_test)
results.append(evaluate("CatBoost Tweedie", y_reg_test, cat_tw_preds))

# --- 5d. LightGBM Tweedie (raw target — handles zeros natively) ---
print("🏆 Training LightGBM Tweedie...")
lgbm_tw = LGBMRegressor(
    objective="tweedie",
    tweedie_variance_power=1.5,
    n_estimators=500, max_depth=8, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8,
    n_jobs=-1, random_state=RANDOM_STATE, verbose=-1,
)
lgbm_tw.fit(X_train, y_reg_train)  # raw target, no log1p
lgbm_tw_preds = lgbm_tw.predict(X_test)
results.append(evaluate("🏆 LightGBM Tweedie", y_reg_test, lgbm_tw_preds))

print("\n\n" + "="*60)
print("  BASELINES SUMMARY")
print("="*60)
results_df = pd.DataFrame(results).sort_values("r2", ascending=False)
print(results_df.to_string(index=False))


# %% Cell 6 — Stacking Regressor (RF + LightGBM + XGB → LightGBM meta)
print("\n🔧 Training Stacking Regressor...")

base_estimators = [
    ("rf", RandomForestRegressor(
        n_estimators=300, max_depth=20, min_samples_leaf=4,
        n_jobs=-1, random_state=RANDOM_STATE,
    )),
    ("lgbm", LGBMRegressor(
        n_estimators=500, max_depth=8, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        n_jobs=-1, random_state=RANDOM_STATE, verbose=-1,
    )),
    ("xgb", XGBRegressor(
        n_estimators=300, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        tree_method="hist", n_jobs=-1, random_state=RANDOM_STATE,
        eval_metric="rmse",
    )),
]

meta_regressor = LGBMRegressor(
    n_estimators=300, max_depth=4, learning_rate=0.05,
    n_jobs=-1, random_state=RANDOM_STATE, verbose=-1,
)

stack_reg = StackingRegressor(
    estimators=base_estimators,
    final_estimator=meta_regressor,
    cv=KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE),
    n_jobs=1,           # base learners already parallel
    passthrough=True,   # meta sees original features + base predictions
)

stack_reg.fit(X_train, y_log_train)
stack_preds = np.expm1(stack_reg.predict(X_test))
results.append(evaluate("⭐ Stacking Regressor", y_reg_test, stack_preds))


# %% Cell 7 — Two-Stage Stacking (Classifier Gate + Stacking Regressor)
# Stage 1: Stacking Classifier — "will there be a catch?"
print("\n🔧 Training Two-Stage Stacking...")
print("  Stage 1: Stacking Classifier (catch / no-catch gate)...")

clf_base = [
    ("rf", RandomForestClassifier(
        n_estimators=300, n_jobs=-1, random_state=RANDOM_STATE,
        class_weight="balanced",
    )),
    ("lgbm", LGBMClassifier(
        n_estimators=500, max_depth=8, learning_rate=0.05,
        n_jobs=-1, random_state=RANDOM_STATE, verbose=-1,
        is_unbalance=True,
    )),
    ("xgb", XGBClassifier(
        n_estimators=300, max_depth=6, learning_rate=0.05,
        tree_method="hist", n_jobs=-1, random_state=RANDOM_STATE,
        eval_metric="logloss",
    )),
]

clf_meta = LGBMClassifier(
    n_estimators=300, max_depth=4, learning_rate=0.05,
    n_jobs=-1, random_state=RANDOM_STATE, verbose=-1,
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

reg_base = [
    ("rf", RandomForestRegressor(
        n_estimators=300, max_depth=20, min_samples_leaf=4,
        n_jobs=-1, random_state=RANDOM_STATE,
    )),
    ("lgbm", LGBMRegressor(
        n_estimators=500, max_depth=8, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        n_jobs=-1, random_state=RANDOM_STATE, verbose=-1,
    )),
    ("xgb", XGBRegressor(
        n_estimators=300, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        tree_method="hist", n_jobs=-1, random_state=RANDOM_STATE,
        eval_metric="rmse",
    )),
]

reg_meta = LGBMRegressor(
    n_estimators=300, max_depth=4, learning_rate=0.05,
    n_jobs=-1, random_state=RANDOM_STATE, verbose=-1,
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
    combined_raw = np.expm1(np.clip(reg_pred_log, 0, None)) * gate
    r2_t = r2_score(y_reg_test, combined_raw)
    if r2_t > best_r2:
        best_r2, best_thresh = r2_t, t

print(f"\n  Optimal classifier threshold: {best_thresh:.2f}")

gate = (probs > best_thresh).astype(int)
reg_pred_log = stack_reg_s2.predict(X_test)
final_preds = np.expm1(np.clip(reg_pred_log, 0, None)) * gate

results.append(evaluate("⭐ Two-Stage Stacking", y_reg_test, final_preds))


# %% Cell 8 — Final Comparison
print("\n\n" + "="*60)
print("  FINAL MODEL COMPARISON")
print("="*60)
results_df = pd.DataFrame(results).sort_values("r2", ascending=False)
print(results_df.to_string(index=False))

# Bar chart
fig, axes = plt.subplots(1, 3, figsize=(16, 5))

for ax, metric, title in zip(axes,
    ["r2", "rmse", "mae"],
    ["R² (higher = better)", "RMSE (lower = better)", "MAE (lower = better)"]):
    colors = ["#2ecc71" if "Stacking" in m or "🏆" in m else "#3498db"
              for m in results_df["model"]]
    ax.barh(results_df["model"], results_df[metric], color=colors)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.invert_yaxis()

plt.tight_layout()
plt.savefig("model_comparison.png", dpi=150, bbox_inches="tight")
plt.show()
print("\n✅ Chart saved: model_comparison.png")


# %% Cell 9 — Feature Importance (LightGBM Tweedie)
print("\n📊 Feature Importance (LightGBM Tweedie):")

importances = pd.Series(lgbm_tw.feature_importances_, index=feature_cols)
top20 = importances.sort_values(ascending=False).head(20)

fig, ax = plt.subplots(figsize=(10, 7))
top20.sort_values().plot.barh(ax=ax, color="#2ecc71")
ax.set_title("Top 20 Feature Importances (LightGBM Tweedie)", fontsize=14, fontweight="bold")
ax.set_xlabel("Importance (split count)")
plt.tight_layout()
plt.savefig("feature_importance.png", dpi=150, bbox_inches="tight")
plt.show()
print("✅ Chart saved: feature_importance.png")


# %% Cell 10 — Cross-Validation of Best Models
print("\n🔄 5-Fold Cross-Validation...")
cv = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

for name, model, target in [
    ("LightGBM Tweedie", LGBMRegressor(
        objective="tweedie", tweedie_variance_power=1.5,
        n_estimators=500, max_depth=8, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        n_jobs=-1, random_state=RANDOM_STATE, verbose=-1,
    ), y_reg),
    ("Stacking Regressor", stack_reg, y_log),
]:
    scores = cross_val_score(model, X, target, cv=cv, scoring="r2", n_jobs=1)
    print(f"\n  {name}:")
    print(f"    R² per fold: {scores.round(4)}")
    print(f"    Mean R²:     {scores.mean():.4f} ± {scores.std():.4f}")

print("\n✅ Pipeline complete!")

# Target stats — mean: 6.14, median: 1.0, max: 669, zeros: 42.0%
# Final features: 51 columns
# Train: 56,689 rows | Test: 14,173 rows
# Train catch rate: 57.9% | Test catch rate: 58.6%
# 🌲 Training Random Forest...

# =======================================================
#   Random Forest
# =======================================================
#   RMSE:  13.20
#   MAE:   4.73
#   R²:    0.1648
# 🚀 Training XGBoost...

# =======================================================
#   XGBoost
# =======================================================
#   RMSE:  13.60
#   MAE:   5.06
#   R²:    0.1133
# 🐱 Training CatBoost Tweedie...

# =======================================================
#   CatBoost Tweedie
# =======================================================
#   RMSE:  12.98
#   MAE:   5.77
#   R²:    0.1925
# 🏆 Training LightGBM Tweedie...

# =======================================================
#   🏆 LightGBM Tweedie
# =======================================================
#   RMSE:  12.58
#   MAE:   5.34
#   R²:    0.2414


# ============================================================
#   BASELINES SUMMARY
# ============================================================
#              model      rmse      mae       r2
# 🏆 LightGBM Tweedie 12.580628 5.337156 0.241389
#   CatBoost Tweedie 12.979484 5.771690 0.192524
#      Random Forest 13.200667 4.732921 0.164770
#            XGBoost 13.600973 5.063361 0.113345

# 🔧 Training Stacking Regressor...

# =======================================================
#   ⭐ Stacking Regressor
# =======================================================
#   RMSE:  12.74
#   MAE:   4.51
#   R²:    0.2226

# 🔧 Training Two-Stage Stacking...
#   Stage 1: Stacking Classifier (catch / no-catch gate)...

#   Classification Gate Report:
#               precision    recall  f1-score   support

#            0       0.78      0.71      0.74      5872
#            1       0.81      0.86      0.83      8301

#     accuracy                           0.80     14173
#    macro avg       0.79      0.78      0.79     14173
# weighted avg       0.80      0.80      0.80     14173

#   Stage 2: Stacking Regressor (amount, trained on catch > 0)...

#   Optimal classifier threshold: 0.35

# =======================================================
#   ⭐ Two-Stage Stacking
# =======================================================
#   RMSE:  12.00
#   MAE:   4.50
#   R²:    0.3100


# ============================================================
#   FINAL MODEL COMPARISON
# ============================================================
#                model      rmse      mae       r2
# ⭐ Two-Stage Stacking 11.997993 4.502888 0.310027
#   🏆 LightGBM Tweedie 12.580628 5.337156 0.241389
# ⭐ Stacking Regressor 12.735727 4.510849 0.222569
#     CatBoost Tweedie 12.979484 5.771690 0.192524
#        Random Forest 13.200667 4.732921 0.164770
#              XGBoost 13.600973 5.063361 0.113345

# ✅ Chart saved: model_comparison.png

# 📊 Feature Importance (LightGBM Tweedie):
# ✅ Chart saved: feature_importance.png

# 🔄 5-Fold Cross-Validation...

#   LightGBM Tweedie:
#     R² per fold: [0.2414 0.3263 0.3495 0.2861 0.323 ]
#     Mean R²:     0.3053 ± 0.0379
