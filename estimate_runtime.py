"""Estimate training time for the XGBoost model via small samples.

The script fits the model on a few fractions of the data and uses a simple
linear regression on the measured runtimes to extrapolate the expected time for
the entire dataset.  This is of course only an approximation; hardware load and
I/O can influence the result.
"""
import os
import time
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor

CSV_PATH = "trips_for_model.csv"
TARGET_COL = "bikes_taken"
TIMESTAMP_COL = "slot_ts"
FRACTIONS = [0.02, 0.05, 0.1]  # sample fractions used for estimation

CORES = os.cpu_count() or 8


def build_pipeline(cat_cols, num_cols):
    preproc = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
            ("num", "passthrough", num_cols),
        ],
        remainder="drop",
    )
    model = XGBRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=8,
        subsample=0.8,
        colsample_bytree=0.8,
        tree_method="hist",
        n_jobs=CORES,
        random_state=42,
    )
    return Pipeline([("preproc", preproc), ("xgb", model)])


def estimate_runtime():
    total_rows = sum(1 for _ in open(CSV_PATH)) - 1
    print(f"Total rows in dataset: {total_rows:,}")

    times = []
    for frac in FRACTIONS:
        rows = max(int(total_rows * frac), 1000)
        print(f"\nUsing {rows:,} rows (~{frac:.0%}) …")

        df = pd.read_csv(CSV_PATH, nrows=rows, low_memory=False)
        df[TIMESTAMP_COL] = pd.to_datetime(df[TIMESTAMP_COL])
        df["hour"] = df[TIMESTAMP_COL].dt.hour
        df["weekday"] = df[TIMESTAMP_COL].dt.dayofweek
        df["is_weekend"] = df["weekday"].isin([5, 6])

        cat_cols = ["temp_class", "season", "hour", "weekday", "cluster_id", "is_weekend"]
        num_cols = (
            df.select_dtypes(include=["number", "bool"])
            .columns.difference(cat_cols + [TARGET_COL, TIMESTAMP_COL])
            .tolist()
        )

        X = df.drop(columns=[TARGET_COL])
        y = df[TARGET_COL]
        pipe = build_pipeline(cat_cols, num_cols)

        start = time.perf_counter()
        pipe.fit(X, y)
        elapsed = time.perf_counter() - start
        times.append((rows, elapsed))
        print(f"  took {elapsed:.1f}s")

    sizes = np.array([t[0] for t in times])
    secs = np.array([t[1] for t in times])
    slope, intercept = np.polyfit(sizes, secs, 1)
    est_total = slope * total_rows + intercept

    print("\nRuntimes used for extrapolation:")
    for r, t in times:
        print(f"  {r:,} rows → {t:.1f}s")

    print(
        f"\nEstimated training time for full dataset: {est_total:.1f}s ({est_total/60:.1f} min)"
    )


if __name__ == "__main__":
    estimate_runtime()
