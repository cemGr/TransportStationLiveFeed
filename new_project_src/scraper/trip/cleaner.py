from __future__ import annotations
from pathlib import Path
import re
import warnings

import pandas as pd

ENCODING = "latin-1"

__all__ = ["TripCleaner"]


class TripCleaner:
    """
    Clean one *raw* Metro ZIP-extracted trip CSV and emit a `*.clean.csv`.

    The logic is 1-for-1 ported from the old `clean_trip_csv()` function – only
    wrapped in an OO façade so we can unit-test and reuse it easily.
    """

    # columns we drop completely
    _DROP_COLS = {
        "trip_id",
        "plan_duration",
        "passholder_type",
        "trip_route_category",
        "duration_imputed",
        "start_time_imputed",
        "end_time_imputed",
        "start_coord_imputed",
        "end_coord_imputed",
        "bike_type_imputed",
    }

    def __init__(self, raw_csv: Path, latest_station_csv: Path, dest_root: Path):
        self.raw = raw_csv
        self.station = latest_station_csv
        self.dest = dest_root
        self.dest.mkdir(parents=True, exist_ok=True)

        self.out_csv = self.dest / self.raw.with_suffix(".clean.csv").name

    # ────────────────────────────────────────────────────────────────────────
    # public API

    def clean(self) -> Path | None:
        if self.out_csv.exists():
            return None

        trips = self._read()
        trips = self._canonicalise_headers(trips)

        # ─── skip files that clearly aren't trip tables ───
        required = {
            "duration", "start_time", "end_time",
            "start_station", "end_station",
            "start_lat", "start_lon",
            "end_lat", "end_lon",
        }
        missing = required - set(trips.columns)
        if missing:
            import warnings
            warnings.warn(
                f"Skipping {self.raw.name}: missing columns {sorted(missing)}"
            )
            return None

        # extract digits, cast to pandas nullable Int64, drop rows without digits
        trips["bike_id"] = (
            trips["bike_id"]
                .astype(str)
                .str.extract(r"(\d+)", expand=False)
                .astype("Int64")
        )
        trips = trips.dropna(subset=["bike_id"])

        # now continue with your existing pipeline
        trips = self._parse_datetimes(trips)
        trips = self._create_imputation_flags(trips)
        trips = self._impute_times(trips)
        trips = self._impute_coords(trips)
        trips = self._impute_bike_type(trips)

        trips = trips.dropna(
            subset=[
                "duration",
                "start_time",
                "end_time",
                "start_station",
                "end_station",
                "start_lat",
                "start_lon",
                "end_lat",
                "end_lon",
            ]
        )

        trips = trips.drop(columns=[c for c in trips.columns if c in self._DROP_COLS])

        trips.to_csv(self.out_csv, index=False)
        print("✓ cleaned", self.raw.name, "→", self.out_csv.name)
        return self.out_csv


    # ────────────────────────────────────────────────────────────────────────
    # private helpers

    def _read(self) -> pd.DataFrame:
        df = pd.read_csv(self.raw, encoding=ENCODING, low_memory=False)
        df.columns = df.columns.str.strip()  # old _strip_cols
        return df

    @staticmethod
    def _canonicalise_headers(df: pd.DataFrame) -> pd.DataFrame:
        df.rename(
            columns=lambda c: re.sub(
                r"_+", "_",
                c.lower().strip().replace("-", "_").replace(" ", "_")
            ),
            inplace=True,
        )
        return df

    @staticmethod
    def _parse_datetimes(df: pd.DataFrame) -> pd.DataFrame:
        df["start_time"] = pd.to_datetime(df["start_time"], format="%m/%d/%Y %H:%M", errors="coerce")
        df["end_time"] = pd.to_datetime(df["end_time"], format="%m/%d/%Y %H:%M", errors="coerce")
        return df

    # flag scaffold
    def _create_imputation_flags(self, df: pd.DataFrame) -> pd.DataFrame:
        flags = [
            "duration_imputed",
            "start_time_imputed",
            "end_time_imputed",
            "start_coord_imputed",
            "end_coord_imputed",
            "bike_type_imputed",
        ]
        for f in flags:
            df[f] = False
        return df

    # ——— imputations ———
    def _impute_times(self, df: pd.DataFrame) -> pd.DataFrame:
        m = df["duration"].isna()
        df.loc[m, "duration"] = (
                (df.loc[m, "end_time"] - df.loc[m, "start_time"]).dt.total_seconds() / 60
        )
        df.loc[m, "duration_imputed"] = True

        m = df["start_time"].isna()
        df.loc[m, "start_time"] = df.loc[m, "end_time"] - pd.to_timedelta(
            df.loc[m, "duration"], unit="m"
        )
        df.loc[m, "start_time_imputed"] = True

        m = df["end_time"].isna()
        df.loc[m, "end_time"] = df.loc[m, "start_time"] + pd.to_timedelta(
            df.loc[m, "duration"], unit="m"
        )
        df.loc[m, "end_time_imputed"] = True
        return df

    def _impute_coords(self, trips: pd.DataFrame) -> pd.DataFrame:
        import warnings

        # load station coords once
        station_df = (
            pd.read_csv(self.station, encoding=ENCODING)
            .rename(columns=lambda c: c.strip())
        )
        lat_map = station_df.set_index("Kiosk ID")["Latitude"]
        lon_map = station_df.set_index("Kiosk ID")["Longitude"]

        for id_col, lat_col, lon_col, flag_col in [
            ("start_station", "start_lat", "start_lon", "start_coord_imputed"),
            ("end_station", "end_lat", "end_lon", "end_coord_imputed"),
        ]:
            # skip if this quarter’s CSV doesn’t even have those columns
            if id_col not in trips.columns or lat_col not in trips.columns or lon_col not in trips.columns:
                warnings.warn(f"Skipping coord imputation: missing columns {id_col}, {lat_col}, or {lon_col}")
                continue

            mask = trips[[lat_col, lon_col]].isna().any(axis=1)
            if not mask.any():
                continue

            # flag and fill
            trips.loc[mask, flag_col] = True
            trips.loc[mask, lat_col] = trips.loc[mask, id_col].map(lat_map)
            trips.loc[mask, lon_col] = trips.loc[mask, id_col].map(lon_map)

        return trips

    @staticmethod
    def _impute_bike_type(df: pd.DataFrame) -> pd.DataFrame:
        if "bike_type" not in df.columns:
            warnings.warn("'bike_type' column missing – filled with 'unknown_device'")
            df["bike_type"] = "unknown_device"
        m = df["bike_type"].isna()
        df.loc[m, "bike_type"] = "unknown_device"
        df.loc[m, "bike_type_imputed"] = True
        return df
