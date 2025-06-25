from __future__ import annotations

import time
from datetime import date, timedelta
from typing import List, Tuple

import pandas as pd
import requests
import requests_cache
from retry_requests import retry

from src.bikemetro.constants import API_URL, BATCH_SIZE

# ────────────────────────────────────────────────────────────────────────────
MAX_SPAN_DAYS     = 14
RATE_LIMIT_SLEEP  = 0.20

class WeatherFetcher:
    def __init__(self, trips_df: pd.DataFrame):
        self.trips = trips_df

    def fetch(self) -> pd.DataFrame:
        if self.trips.empty:
            return self._empty_frame()

        start_date = self.trips["start_time"].min().date()
        end_date   = self.trips["start_time"].max().date()

        # unique start-station coordinates
        coords = list(
            self.trips[["start_lat", "start_lon"]]
            .drop_duplicates()
            .itertuples(index=False, name=None)
        )

        session: requests.Session = retry(
            requests_cache.CachedSession("weather_cache", expire_after=3600)
        )

        frames: list[pd.DataFrame] = []
        for i in range(0, len(coords), BATCH_SIZE):
            batch = coords[i : i + BATCH_SIZE]
            for d0, d1 in self._date_windows(start_date, end_date):
                frames.append(self._fetch_window(session, batch, d0, d1))

        return pd.concat(frames, ignore_index=True) if frames else self._empty_frame()

    @staticmethod
    def _date_windows(d0: date, d1: date):
        """Yield (start, end) windows with length ≤ MAX_SPAN_DAYS."""
        cur = d0
        one = timedelta(days=1)
        span = timedelta(days=MAX_SPAN_DAYS - 1)
        while cur <= d1:
            nxt = min(cur + span, d1)
            yield cur, nxt
            cur = nxt + one

    def _fetch_window(
        self,
        session: requests.Session,
        coords: List[Tuple[float, float]],
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        lat = ",".join(f"{c[0]:.5f}" for c in coords)
        lon = ",".join(f"{c[1]:.5f}" for c in coords)

        params = {
            "latitude":   lat,
            "longitude":  lon,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date":   end_date.strftime("%Y-%m-%d"),
            "hourly":     "temperature_2m,rain,weathercode",
            "timezone":   "UTC",
        }

        for attempt in range(3):
            r = session.get(API_URL, params=params, timeout=30)
            if r.status_code != 429:
                break
            sleep_time = 2 ** attempt
            time.sleep(sleep_time)
        r.raise_for_status()

        df = self._json_to_df(r.json())
        time.sleep(RATE_LIMIT_SLEEP)
        return df

    @staticmethod
    def _json_to_df(data) -> pd.DataFrame:
        if isinstance(data, dict):
            data = [data]

        rows = []
        for item in data:
            lat0 = item.get("latitude")
            lon0 = item.get("longitude")
            hourly = item.get("hourly", {})
            for t, temp, rain, code in zip(
                hourly.get("time", []),
                hourly.get("temperature_2m", []),
                hourly.get("rain", []),
                hourly.get("weathercode", []),
            ):
                rows.append(
                    {
                        "time": pd.to_datetime(t),
                        "latitude": lat0,
                        "longitude": lon0,
                        "temperature_2m": temp,
                        "rain": rain,
                        "weather_code": code,
                    }
                )
        return pd.DataFrame(rows)

    @staticmethod
    def _empty_frame() -> pd.DataFrame:
        return pd.DataFrame(
            columns=[
                "time",
                "latitude",
                "longitude",
                "temperature_2m",
                "rain",
                "weather_code",
            ]
        )
