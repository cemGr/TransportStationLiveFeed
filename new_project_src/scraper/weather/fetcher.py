from datetime import date
from typing import List, Tuple
import pandas as pd
import requests
import requests_cache
from retry_requests import retry

from new_project_src.bikemetro.constants import API_URL, BATCH_SIZE

class WeatherFetcher:
    """
    Given a DataFrame of trips, fetch hourly weather from Open-Meteo
    for each unique (lat, lon) between min and max trip dates.
    """

    def __init__(self, trips_df: pd.DataFrame):
        self.trips = trips_df

    def fetch(self) -> pd.DataFrame:
        start_date = self.trips["start_time"].min().date()
        end_date   = self.trips["start_time"].max().date()

        coords = list(
            self.trips[["start_lat", "start_lon"]]
                .drop_duplicates()
                .itertuples(index=False, name=None)
        )

        session = retry(requests_cache.CachedSession("weather_cache", expire_after=3600))
        frames = []
        for i in range(0, len(coords), BATCH_SIZE):
            batch = coords[i : i + BATCH_SIZE]
            frames.append(self._fetch_batch(session, batch, start_date, end_date))

        if frames:
            return pd.concat(frames, ignore_index=True)
        return pd.DataFrame(
            columns=[
                "time", "latitude", "longitude",
                "temperature_2m", "rain", "weather_code"
            ]
        )

    def _fetch_batch(
        self,
        session: requests.Session,
        coords: List[Tuple[float, float]],
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        lat = ",".join(f"{c[0]:.5f}" for c in coords)
        lon = ",".join(f"{c[1]:.5f}" for c in coords)
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date":   end_date.strftime("%Y-%m-%d"),
            "hourly": "temperature_2m,rain,weathercode",
            "timezone": "UTC",
        }
        r = session.get(API_URL, params=params)
        r.raise_for_status()
        data = r.json()
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
                rows.append({
                    "time": pd.to_datetime(t),
                    "latitude": lat0,
                    "longitude": lon0,
                    "temperature_2m": temp,
                    "rain": rain,
                    "weather_code": code,
                })
        return pd.DataFrame(rows)
