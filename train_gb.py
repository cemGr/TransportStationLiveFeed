"""Train Gradient Boosting model (XGBoost) for bike demand forecasting."""
import os, time, math
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from joblib import dump
from xgboost import XGBRegressor

CSV_PATH = "trips_for_model.csv"
TARGET_COL = "bikes_taken"
TIMESTAMP_COL = "slot_ts"
CORES = os.cpu_count() or 8

# 1. load data
if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(CSV_PATH)

df = pd.read_csv(CSV_PATH, low_memory=False)
if TIMESTAMP_COL not in df.columns:
    raise KeyError(f"Column '{TIMESTAMP_COL}' not found")

df[TIMESTAMP_COL] = pd.to_datetime(df[TIMESTAMP_COL])

# 2. feature engineering

df["hour"] = df[TIMESTAMP_COL].dt.hour
df["weekday"] = df[TIMESTAMP_COL].dt.dayofweek
df["is_weekend"] = df["weekday"].isin([5, 6])

cat_cols = ["temp_class","season","hour","weekday","cluster_id","is_weekend"]
num_cols = (
    df.select_dtypes(include=["number","bool"])
      .columns.difference(cat_cols + [TARGET_COL, TIMESTAMP_COL])
      .tolist()
)

preproc = ColumnTransformer([
    ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
    ("num", "passthrough", num_cols),
], remainder="drop")

# 3. split train/val/test (time-based)

df = df.sort_values(TIMESTAMP_COL)
n = len(df)
train_end = math.floor(n * 0.70)
val_end = math.floor(n * 0.85)
train = df.iloc[:train_end]
val = df.iloc[train_end:val_end]
test = df.iloc[val_end:]

X_train, y_train = train.drop(columns=[TARGET_COL]), train[TARGET_COL]
X_val,   y_val   = val.drop(columns=[TARGET_COL]),   val[TARGET_COL]
X_test,  y_test  = test.drop(columns=[TARGET_COL]),  test[TARGET_COL]

# 4. build model

xgb_params = dict(
    n_estimators=500,
    learning_rate=0.05,
    max_depth=8,
    subsample=0.8,
    colsample_bytree=0.8,
    tree_method="hist",
    n_jobs=CORES,
    random_state=42,
)

model = Pipeline([
    ("preproc", preproc),
    ("xgb", XGBRegressor(**xgb_params)),
])

# 5. train
print("\u23F3 Training XGBoost …")
t0 = time.perf_counter()
model.fit(pd.concat([X_train, X_val]), pd.concat([y_train, y_val]))
train_time = time.perf_counter() - t0
print(f"Training finished in {train_time:.1f}s")

# 6. evaluate

y_pred = model.predict(X_test)
metrics = {
    "Test MAE": mean_absolute_error(y_test, y_pred),
    "Test RMSE": np.sqrt(mean_squared_error(y_test, y_pred)),
    "Test R2": r2_score(y_test, y_pred),
}

with open("xgb_evaluation_metrics.txt", "w") as f:
    for m, v in metrics.items():
        f.write(f"{m}: {v:.3f}\n")
print("Metrics saved to xgb_evaluation_metrics.txt")

dump(model, "xgb_model.pkl")
print("Model saved to xgb_model.pkl")
