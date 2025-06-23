"""Estimate training runtime for the XGBoost model on the full dataset."""
import os, time, math
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor

CSV_PATH = "trips_for_model.csv"
TARGET_COL = "bikes_taken"
TIMESTAMP_COL = "slot_ts"
SAMPLE_FRAC = 0.05  # use 5% of rows to estimate runtime

CORES = os.cpu_count() or 8


def build_pipeline(cat_cols, num_cols):
    preproc = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
        ("num", "passthrough", num_cols),
    ], remainder="drop")
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


def estimate_runtime(sample_frac=SAMPLE_FRAC):
    total_rows = sum(1 for _ in open(CSV_PATH)) - 1
    sample_rows = max(int(total_rows * sample_frac), 1000)
    print(f"Total rows: {total_rows:,}. Using {sample_rows:,} rows for estimate...")

    df = pd.read_csv(CSV_PATH, nrows=sample_rows, low_memory=False)
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
    est_total = elapsed / sample_frac

    print(f"Fitting on sample took {elapsed:.1f}s")
    print(f"Estimated runtime for full dataset: {est_total:.1f}s ({est_total/60:.1f} min)")


if __name__ == "__main__":
    estimate_runtime()
