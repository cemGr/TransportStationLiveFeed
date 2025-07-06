import os
import time
import math
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.experimental import enable_halving_search_cv  # noqa: F401
from sklearn.model_selection import TimeSeriesSplit, HalvingRandomSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from joblib import dump, parallel_backend

CSV_PATH = "trips_for_model.csv"
TIMESTAMP_COL = "slot_ts"
TARGETS = ["bikes_taken", "bikes_returned"]
CORES = os.cpu_count() or 8
os.environ["OMP_NUM_THREADS"] = "1"

if not os.path.exists(CSV_PATH) and os.path.exists("trips_for_model.zip"):
    import zipfile
    with zipfile.ZipFile("trips_for_model.zip") as zf:
        zf.extract(CSV_PATH)

print("Loading data …")
df = pd.read_csv(CSV_PATH, low_memory=False)
if TIMESTAMP_COL not in df.columns:
    raise KeyError(f"Column {TIMESTAMP_COL} not found")
df[TIMESTAMP_COL] = pd.to_datetime(df[TIMESTAMP_COL])

print("Creating features …")

# sort by station+time so lag/rolling features make sense
df = df.sort_values(["station_id", TIMESTAMP_COL])

df["hour"] = df[TIMESTAMP_COL].dt.hour
df["weekday"] = df[TIMESTAMP_COL].dt.dayofweek

# cyclical encoding of hour and weekday
df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
df["wd_sin"] = np.sin(2 * np.pi * df["weekday"] / 7)
df["wd_cos"] = np.cos(2 * np.pi * df["weekday"] / 7)
df["is_weekend"] = df["weekday"].isin([5, 6])

# lag and rolling mean features per station
for t in TARGETS:
    df[f"{t}_lag1"] = (
        df.groupby("station_id")[t].shift(1).fillna(0)
    )
    df[f"{t}_roll3"] = (
        df.groupby("station_id")[t]
          .rolling(window=3, min_periods=1)
          .mean()
          .reset_index(level=0, drop=True)
          .fillna(0)
    )

cat_cols = ["temp_class", "season", "cluster_id", "is_weekend"]
num_cols = (
    df.select_dtypes(include=["number", "bool"])
      .columns.difference(cat_cols + TARGETS + [TIMESTAMP_COL, "hour", "weekday"])
      .tolist()
)

preproc = ColumnTransformer(
    [
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
        ("num", "passthrough", num_cols),
    ]
)

# sort once for time series split
df = df.sort_values(TIMESTAMP_COL)

results = {}
models = {}

for target in TARGETS:
    print(f"\n=== Training model for {target} ===")
    n = len(df)
    train_end = math.floor(n * 0.70)
    val_end = math.floor(n * 0.85)

    train = df.iloc[:train_end]
    val = df.iloc[train_end:val_end]
    test = df.iloc[val_end:]

    drop_cols = [t for t in TARGETS if t != target]
    X_train, y_train = train.drop(columns=drop_cols), train[target]
    X_val, y_val = val.drop(columns=drop_cols), val[target]
    X_test, y_test = test.drop(columns=drop_cols), test[target]

    baseline = Pipeline([
        ("preproc", preproc),
        ("rf", RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1, verbose=0)),
    ])
    baseline.fit(X_train, y_train)
    base_mae = mean_absolute_error(y_val, baseline.predict(X_val))
    print(f"Baseline MAE: {base_mae:.3f}")

    rf_search = RandomForestRegressor(n_estimators=50, random_state=42, n_jobs=1)
    param_dist = {
        "rf__max_depth": [None, 8, 12, 16, 20],
        "rf__max_features": ["sqrt", 0.3, 0.5, 0.7],
        "rf__min_samples_leaf": [1, 2, 4],
        "rf__min_samples_split": [2, 5, 10],
    }
    pipe = Pipeline([("preproc", preproc), ("rf", rf_search)])
    tscv = TimeSeriesSplit(n_splits=3)
    search = HalvingRandomSearchCV(
        estimator=pipe,
        param_distributions=param_dist,
        n_candidates=70,
        factor=3,
        resource="rf__n_estimators",
        max_resources=300,
        min_resources=50,
        random_state=42,
        cv=tscv,
        scoring="neg_mean_absolute_error",
        n_jobs=CORES,
        verbose=0,
    )

    with parallel_backend("loky"):
        search.fit(pd.concat([X_train, X_val]), pd.concat([y_train, y_val]))

    best_params = {k.split("__", 1)[1]: v for k, v in search.best_params_.items()}
    best_params.update(dict(n_estimators=600, random_state=42, n_jobs=CORES))

    final_model = Pipeline([
        ("preproc", preproc),
        ("rf", RandomForestRegressor(**best_params)),
    ])
    with parallel_backend("loky"):
        final_model.fit(pd.concat([X_train, X_val]), pd.concat([y_train, y_val]))

    y_pred = final_model.predict(X_test)
    metrics = {
        "Test MAE": mean_absolute_error(y_test, y_pred),
        "Test RMSE": np.sqrt(mean_squared_error(y_test, y_pred)),
        "Test R2": r2_score(y_test, y_pred),
    }
    results[target] = metrics
    models[target] = final_model

    dump(final_model, f"rf_{target}.pkl")
    with open(f"evaluation_{target}.txt", "w") as f:
        for m, v in metrics.items():
            f.write(f"{m}: {v:.3f}\n")
    print(f"Saved model rf_{target}.pkl")

print("\nEvaluating net bike usage …")
X_test = df.iloc[val_end:].drop(columns=TARGETS)
y_net = df.iloc[val_end:]["bikes_taken"] - df.iloc[val_end:]["bikes_returned"]
pred_net = models["bikes_taken"].predict(X_test) - models["bikes_returned"].predict(X_test)
net_metrics = {
    "Net MAE": mean_absolute_error(y_net, pred_net),
    "Net RMSE": np.sqrt(mean_squared_error(y_net, pred_net)),
    "Net R2": r2_score(y_net, pred_net),
}
with open("evaluation_net.txt", "w") as f:
    for m, v in net_metrics.items():
        f.write(f"{m}: {v:.3f}\n")
print("Net metrics saved to evaluation_net.txt")
