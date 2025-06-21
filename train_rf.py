import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from joblib import dump

TARGET_COL = "bikes_taken"  # change if your target column has a different name
CSV_PATH = "trips_for_model.csv"

def main() -> None:
    # ------------------------------------------------------------------ 1. Load
    df = pd.read_csv(CSV_PATH, parse_dates=["slot_ts"])

    # --------------------------------------------------------- 2. Feature eng.
    df["hour"] = df["slot_ts"].dt.hour
    df["weekday"] = df["slot_ts"].dt.dayofweek
    df["is_weekend"] = df["weekday"].isin([5, 6])

    cat_cols = ["temp_class", "season", "hour", "weekday", "cluster_id", "is_weekend"]
    num_cols = [c for c in df.columns if c not in cat_cols + [TARGET_COL, "slot_ts"]]

    preproc = ColumnTransformer(
        [("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols)],
        remainder="passthrough",
    )

    # ----------------------------------------------------------- 3. Time split
    df = df.sort_values("slot_ts")
    n = len(df)
    n_train = int(n * 0.70)
    n_val = int(n * 0.15)

    train = df.iloc[:n_train]
    val = df.iloc[n_train:n_train + n_val]
    test = df.iloc[n_train + n_val:]

    X_train, y_train = train.drop(columns=[TARGET_COL]), train[TARGET_COL]
    X_val, y_val = val.drop(columns=[TARGET_COL]), val[TARGET_COL]
    X_test, y_test = test.drop(columns=[TARGET_COL]), test[TARGET_COL]

    # ---------------------------------------------------- 4. Baseline RF model
    baseline = Pipeline(
        [
            ("preproc", preproc),
            (
                "rf",
                RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1),
            ),
        ]
    )
    baseline.fit(X_train, y_train)
    val_pred = baseline.predict(X_val)
    print("Baseline MAE:", mean_absolute_error(y_val, val_pred))

    # ------------------------------------------------------ 5. GridSearch + CV
    full_X = pd.concat([X_train, X_val], axis=0)
    full_y = pd.concat([y_train, y_val], axis=0)
    tscv = TimeSeriesSplit(n_splits=5)

    param_grid = {
        "rf__n_estimators": [200, 300, 400],
        "rf__max_depth": [None, 10, 20, 30],
        "rf__max_features": ["auto", "sqrt", 0.5],
    }

    search = GridSearchCV(
        Pipeline(
            [
                ("preproc", preproc),
                ("rf", RandomForestRegressor(random_state=42, n_jobs=-1)),
            ]
        ),
        param_grid=param_grid,
        cv=tscv,
        scoring="neg_mean_absolute_error",
        n_jobs=-1,
    )
    search.fit(full_X, full_y)
    best_model = search.best_estimator_
    print("Best parameters:", search.best_params_)

    # ---------------------------------------------------------- 6. Evaluation
    test_pred = best_model.predict(X_test)
    mae = mean_absolute_error(y_test, test_pred)
    rmse = mean_squared_error(y_test, test_pred, squared=False)
    r2 = r2_score(y_test, test_pred)
    print(f"Test MAE: {mae:.3f}")
    print(f"Test RMSE: {rmse:.3f}")
    print(f"Test R²: {r2:.3f}")

    feat_names = best_model.named_steps["preproc"].get_feature_names_out()
    importances = best_model.named_steps["rf"].feature_importances_
    idx = np.argsort(importances)[::-1][:10]
    print("\nTop-10 feature importances:")
    for i in idx:
        print(f"{feat_names[i]}: {importances[i]:.4f}")

    # --------------------------------------------------------------- 7. Save
    dump(best_model, "rf_hourly.pkl")
    print("Model saved to rf_hourly.pkl")


if __name__ == "__main__":
    main()
