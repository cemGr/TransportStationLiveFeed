from __future__ import annotations

import re
import warnings

import pandas as pd
from pathlib import Path

ENCODING = "latin-1"

# ---------------------------------------------------------------------- helpers
def _strip_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.strip()
    return df

def _parse_datetime(col: pd.Series) -> pd.Series:
    return pd.to_datetime(col, format="%m/%d/%Y %H:%M", errors="coerce")

def _canonicalise_headers(df: pd.DataFrame) -> pd.DataFrame:

    df.rename(
        columns=lambda c: re.sub(r"_+", "_",
                                 c.lower().strip().replace("-", "_")
                                               .replace(" ", "_")),
        inplace=True,
    )
    return df

def ensure_column(df: pd.DataFrame, name: str,
                  default_value=None, warn_msg: str | None = None) -> None:

    if name not in df.columns:
        if warn_msg:
            warnings.warn(warn_msg, stacklevel=2)
        df[name] = default_value
# ---------------------------------------------------------------------- station
def clean_station_csv(src: Path, dest_root: Path) -> Path:
    dest_root.mkdir(parents=True, exist_ok=True)
    out = dest_root / "cleaned_station_data.csv"

    df = pd.read_csv(src, encoding=ENCODING)
    df = _strip_cols(df)
    df = (
        df.drop_duplicates(subset=["Kiosk ID"])
          .assign(
              Region      = lambda d: d["Region"].fillna("Unknown"),
              **{
                  "Kiosk Name": lambda d: d["Kiosk Name"].fillna("Unnamed Station"),
                  "Status":     lambda d: d["Status"].fillna("Unknown"),
                  "status2":    lambda d: d["status2"].fillna("Unknown"),
              }
          )
          .drop(columns=["Go Live Date", "status2"])
    )

    df.to_csv(out, index=False)
    print("✓ cleaned station →", out.name)
    return out

# ---------------------------------------------------------------------- trip
_DROP_COLS = [
    "trip_id", "plan_duration", "passholder_type", "trip_route_category",
    "duration_imputed", "start_time_imputed", "end_time_imputed",
    "start_coord_imputed", "end_coord_imputed", "bike_type_imputed",
]

def _impute_times(df: pd.DataFrame) -> pd.DataFrame:
    # duration
    m = df["duration"].isna()
    df.loc[m, "duration"] = (
        (df.loc[m, "end_time"] - df.loc[m, "start_time"]).dt.total_seconds() / 60
    )
    df.loc[m, "duration_imputed"] = True

    # start_time
    m = df["start_time"].isna()
    df.loc[m, "start_time"] = df.loc[m, "end_time"] - pd.to_timedelta(
        df.loc[m, "duration"], unit="m"
    )
    df.loc[m, "start_time_imputed"] = True

    # end_time
    m = df["end_time"].isna()
    df.loc[m, "end_time"] = df.loc[m, "start_time"] + pd.to_timedelta(
        df.loc[m, "duration"], unit="m"
    )
    df.loc[m, "end_time_imputed"] = True
    return df


def _impute_coords(
    trips: pd.DataFrame,
    stations: pd.DataFrame,
    id_col: str,
    lat_col: str,
    lon_col: str,
    flag_col: str,
) -> pd.DataFrame:
    mask = trips[[lat_col, lon_col]].isna().any(axis=1)
    if not mask.any():
        return trips
    trips.loc[mask, flag_col] = True
    trips = trips.merge(
        stations[["Kiosk ID", "Latitude", "Longitude"]],
        how="left",
        left_on=id_col,
        right_on="Kiosk ID",
    )
    trips.loc[mask, lat_col] = trips.loc[mask, "Latitude"]
    trips.loc[mask, lon_col] = trips.loc[mask, "Longitude"]
    return trips.drop(columns=["Kiosk ID", "Latitude", "Longitude"])


def clean_trip_csv(
    src: Path, latest_station_csv: Path, dest_root: Path
) -> Path | None:
    dest_root.mkdir(parents=True, exist_ok=True)
    out = dest_root / src.with_suffix(".clean.csv").name
    if out.exists():
        return None

    # ▸ read
    trips = pd.read_csv(src, encoding=ENCODING, low_memory=False)
    trips = _strip_cols(trips)
    trips = _canonicalise_headers(trips)

    # TODO: ▸ unique case bike_type not always a table
    ensure_column(
        trips,
        "bike_type",
        default_value="unknown_device",
        warn_msg=f"'bike_type' column missing in {src.name} – filled with 'unknown_device'"
    )
    # ▸ date parsing
    trips["start_time"] = _parse_datetime(trips["start_time"])
    trips["end_time"]   = _parse_datetime(trips["end_time"])

    # ▸ imputation flags
    flags = [
        "duration_imputed",
        "start_time_imputed",
        "end_time_imputed",
        "start_coord_imputed",
        "end_coord_imputed",
        "bike_type_imputed",
    ]
    for f in flags:
        trips[f] = False

    trips = _impute_times(trips)

    # ▸ coords via station table
    station_df = pd.read_csv(latest_station_csv, encoding=ENCODING)
    station_df = _strip_cols(station_df)
    trips = _impute_coords(trips, station_df, "start_station", "start_lat", "start_lon",
                           "start_coord_imputed")
    trips = _impute_coords(trips, station_df, "end_station", "end_lat", "end_lon",
                           "end_coord_imputed")

    # ▸ bike_type nan
    m = trips["bike_type"].isna()
    trips.loc[m, "bike_type"] = "unknown_device"
    trips.loc[m, "bike_type_imputed"] = True

    # ▸ essential rows only
    essential = [
        "duration", "start_time", "end_time",
        "start_station", "end_station",
        "start_lat", "start_lon", "end_lat", "end_lon",
    ]
    trips = trips.dropna(subset=essential)

    # ▸ final drop + save
    trips = trips.drop(columns=_DROP_COLS)
    trips.to_csv(out, index=False)
    print("✓ cleaned", src.name, "→", out.name)
    return out
