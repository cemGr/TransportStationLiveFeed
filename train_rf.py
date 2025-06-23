"""
Bike-demand forecasting – fast RandomForest tune on Apple M-series
=================================================================
• RandomForest *only*  – no model change
• Successive-halving search (~15% of the fits a full grid would need)
• Uses all CPU cores once (outer CV n_jobs = –1, trees single-threaded)

Requires: scikit-learn ≥ 1.4, pandas, numpy, joblib
-----------------------------------------------------------------
pip install -U scikit-learn pandas numpy joblib
"""

# ---------- imports & env -----------------------------------------------
import os, time, math
import argparse
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.experimental import enable_halving_search_cv

from sklearn.model_selection import (
    TimeSeriesSplit,
    HalvingRandomSearchCV,
)
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from joblib import dump, parallel_backend

parser = argparse.ArgumentParser(description="Train RandomForest demand model")
parser.add_argument(
    "--target",
    choices=["bikes_taken", "bikes_returned", "net_usage"],
    default="bikes_taken",
    help="target column to predict",
)
args = parser.parse_args()

# ---------- config -------------------------------------------------------
CSV_PATH      = "trips_for_model.csv"
TARGET_COL    = args.target
TIMESTAMP_COL = "slot_ts"
CORES         = os.cpu_count() or 8       # M4 Pro shows 12–14

# keep each tree single-threaded → no nested OpenMP contention
os.environ["OMP_NUM_THREADS"] = "1"

# ---------- 1. load ------------------------------------------------------
df = pd.read_csv(CSV_PATH, low_memory=False)
if TIMESTAMP_COL not in df.columns:
    raise KeyError(f"Column “{TIMESTAMP_COL}” not found.")
df[TIMESTAMP_COL] = pd.to_datetime(df[TIMESTAMP_COL])

# create net_usage if possible
if {"bikes_taken", "bikes_returned"}.issubset(df.columns):
    df["net_usage"] = df["bikes_returned"] - df["bikes_taken"]

if TARGET_COL not in df.columns:
    raise KeyError(f"Target column '{TARGET_COL}' not found.")

# ---------- 2. feature engineering --------------------------------------
df["hour"]       = df[TIMESTAMP_COL].dt.hour
df["weekday"]    = df[TIMESTAMP_COL].dt.dayofweek
df["is_weekend"] = df["weekday"].isin([5, 6])

cat_cols = ["temp_class", "season", "hour",
            "weekday", "cluster_id", "is_weekend"]
num_cols = (
    df.select_dtypes(include=["number", "bool"])
      .columns.difference(cat_cols + [TARGET_COL, TIMESTAMP_COL])
      .tolist()
)

preproc = ColumnTransformer(
    [("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
     ("num", "passthrough",                            num_cols)],
    remainder="drop",
)

# ---------- 3. time-split train / val / test -----------------------------
df = df.sort_values(TIMESTAMP_COL)
n  = len(df)
train_end = math.floor(n * 0.70)
val_end   = math.floor(n * 0.85)

train = df.iloc[:train_end]
val   = df.iloc[train_end:val_end]
test  = df.iloc[val_end:]

X_train, y_train = train.drop(columns=[TARGET_COL]), train[TARGET_COL]
X_val,   y_val   = val.drop(columns=[TARGET_COL]),   val[TARGET_COL]
X_test,  y_test  = test.drop(columns=[TARGET_COL]),  test[TARGET_COL]

# ---------- 4. quick baseline RF (200 trees) -----------------------------
baseline = Pipeline([
    ("preproc", preproc),
    ("rf", RandomForestRegressor(
            n_estimators=200,
            random_state=42,
            n_jobs=-1,        # forest parallelism OK for *one* fit
            verbose=2))
])
t0 = time.perf_counter()
baseline.fit(X_train, y_train)
print(f"Baseline RF in {time.perf_counter()-t0:.1f}s – "
      f"val MAE {mean_absolute_error(y_val, baseline.predict(X_val)):.3f}")

# ---------- 5. successive-halving hyper-search (RandomForest) -----------
rf_search = RandomForestRegressor(
        n_estimators=50,      # tiny resource for first round
        random_state=42,
        n_jobs=1)            # <-- trees serial, CV parallel

param_dist = {
    "rf__max_depth":           [None, 8, 12, 16, 20],
    "rf__max_features":        ["sqrt", 0.3, 0.5, 0.7],
    "rf__min_samples_leaf":    [1, 2, 4],
    "rf__min_samples_split":   [2, 5, 10],
}

pipe = Pipeline([("preproc", preproc),
                 ("rf", rf_search)])

tscv = TimeSeriesSplit(n_splits=3)

search = HalvingRandomSearchCV(
    estimator           = pipe,
    param_distributions = param_dist,
    n_candidates        = 70,          # start ideas
    factor              = 3,           # keep best 1/3 each iteration
    resource            = "rf__n_estimators",
    max_resources       = 300,         # final round = 300-tree forests
    min_resources       = 50,
    random_state        = 42,
    cv                  = tscv,
    scoring             = "neg_mean_absolute_error",
    n_jobs              = CORES,       # one fit per core
    verbose             = 3,
)

print("\n⏳ Successive-halving search (RandomForest)…")
t0 = time.perf_counter()
with parallel_backend("loky"):
    search.fit(pd.concat([X_train, X_val]),
               pd.concat([y_train, y_val]))
print(f"Search finished in {time.perf_counter()-t0:.1f}s")
print("Best params:", search.best_params_)

# ---------- 6. refit best params on FULL train+val with 600 trees ---------
best_rf_params = {k.split("__", 1)[1]: v for k, v in search.best_params_.items()}
best_rf_params.update(dict(n_estimators=600,
                           random_state=42,
                           n_jobs=CORES))   # final forest uses all cores

final_model = Pipeline([
    ("preproc", preproc),
    ("rf", RandomForestRegressor(**best_rf_params))
])

print("\n⏳ Final RandomForest (600 trees)…")
t0 = time.perf_counter()
with parallel_backend("loky"):
    final_model.fit(pd.concat([X_train, X_val]),
                    pd.concat([y_train, y_val]))
print(f"Final fit done in {time.perf_counter()-t0:.1f}s")

# ---------- 7. evaluation -------------------------------------------------
# Save evaluation metrics to a file
y_pred = final_model.predict(X_test)
metrics = {
    "Test MAE": mean_absolute_error(y_test, y_pred),
    "Test RMSE": np.sqrt(mean_squared_error(y_test, y_pred)),
    "Test R²": r2_score(y_test, y_pred),
}

with open("evaluation_metrics.txt", "w") as f:
    for metric, value in metrics.items():
        f.write(f"{metric}: {value:.3f}\n")

# Save feature importances to a file
feat_names = final_model.named_steps["preproc"].get_feature_names_out()
imps = final_model.named_steps["rf"].feature_importances_
top = np.argsort(imps)[::-1][:10]

with open("feature_importances.txt", "w") as f:
    f.write("Top-10 feature importances:\n")
    for i in top:
        f.write(f"{feat_names[i]}: {imps[i]:.4f}\n")

print("\nEvaluation metrics and feature importances saved to files.")

# ---------- 8. save -------------------------------------------------------
dump(final_model, "rf_hourly.pkl")
print("\n✅  Model saved to rf_hourly.pkl")

