"""Weather service for Open-Meteo aggregation."""
from __future__ import annotations

from datetime import datetime
from typing import List, Tuple, Optional

import logging

import pandas as pd
import requests
import requests_cache
from retry_requests import retry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
try:
    from sklearn.cluster import KMeans  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    class KMeans:  # type: ignore
        def __init__(self, n_clusters: int = 8, random_state: int | None = None):
            self.n_clusters = n_clusters

        def fit_predict(self, X):
            return [0] * len(X)

from infrastructure.db import open_connection

API_URL = "https://archive-api.open-meteo.com/v1/archive"
BATCH_SIZE = 50
TRIP_BATCH_SIZE = 60000  # process roughly 50k-70k trips per run


def load_trips(
    conn,
    since: Optional[datetime] = None,
    limit: int = TRIP_BATCH_SIZE,
) -> pd.DataFrame:
    """Load a batch of trip rows from the database."""
    
    logging.info("Loading up to %s trips since %s", limit, since)
    sql = (
        "SELECT start_time, end_time, start_station, end_station, "
        "start_lat, start_lon, end_lat, end_lon FROM public.trips"
    )
    params: List = []
    if since is not None:
        sql += " WHERE start_time > %s"
        params.append(since)
    sql += " ORDER BY start_time LIMIT %s"
    params.append(limit)

    df = pd.read_sql_query(sql, conn, params=params, parse_dates=["start_time", "end_time"])
    logging.info("Loaded %s trips", len(df))
    return df



def _fetch_batch(
    session: requests.Session,
    coords: List[Tuple[float, float]],
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    """Fetch a batch of hourly weather for the given coordinates."""
    logging.debug(
        "Requesting weather for %s coords from %s to %s",
        len(coords),
        start_date,
        end_date,
    )
    lat = ",".join(f"{c[0]:.5f}" for c in coords)
    lon = ",".join(f"{c[1]:.5f}" for c in coords)
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
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
        lat = item.get("latitude")
        lon = item.get("longitude")
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
                    "latitude": lat,
                    "longitude": lon,
                    "temperature_2m": temp,
                    "rain": rain,
                    "weather_code": code,
                }
            )
    return pd.DataFrame(rows)


def fetch_weather(df: pd.DataFrame) -> pd.DataFrame:
    """Query Open-Meteo for unique station coordinates."""
    start_date = df["start_time"].min().date()
    end_date = df["start_time"].max().date()
    coords = (
        df[["start_lat", "start_lon"]]
        .drop_duplicates()
        .itertuples(index=False, name=None)
    )
    coords = list(coords)
    logging.info(
        "Fetching weather for %s coordinates from %s to %s",
        len(coords),
        start_date,
        end_date,
    )
    session = retry(requests_cache.CachedSession("weather", expire_after=3600))
    frames = []
    for i in range(0, len(coords), BATCH_SIZE):
        batch = coords[i : i + BATCH_SIZE]
        frames.append(_fetch_batch(session, batch, start_date, end_date))
    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame(
        columns=["time", "latitude", "longitude", "temperature_2m", "rain", "weather_code"]
    )


def compute_aggregates(trips: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    """Compute hourly trip and weather aggregates."""
    logging.info("Computing aggregates for %s trips and %s weather rows", len(trips), len(weather))
    df = trips.copy()
    df["slot_ts"] = df["start_time"].dt.floor("h")
    df["hour_of_day"] = df["slot_ts"].dt.hour
    df["weekday_num"] = df["slot_ts"].dt.weekday
    df["is_weekend"] = df["weekday_num"].isin([5, 6])

    stations = (
        df[["start_station", "start_lat", "start_lon"]]
        .drop_duplicates()
        .rename(columns={"start_station": "station_id", "start_lat": "lat", "start_lon": "lon"})
    )
    if not stations.empty:
        kmeans = KMeans(n_clusters=min(80, len(stations)), random_state=0)
        stations["cluster_id"] = kmeans.fit_predict(stations[["lat", "lon"]])
    else:
        stations["cluster_id"] = []

    taken = df.groupby(["slot_ts", "start_station"]).size().reset_index(name="bikes_taken")
    returned = df.groupby(["slot_ts", "end_station"]).size().reset_index(name="bikes_returned")
    agg = (
        pd.merge(taken, returned, left_on=["slot_ts", "start_station"], right_on=["slot_ts", "end_station"], how="outer")
        .rename(columns={"start_station": "station_id"})
    )
    agg["station_id"] = agg["station_id"].fillna(agg["end_station"]).astype(int)
    agg = agg.drop(columns="end_station")
    agg[["bikes_taken", "bikes_returned"]] = agg[["bikes_taken", "bikes_returned"]].fillna(0).astype(int)

    weather["slot_ts"] = pd.to_datetime(weather["time"]).dt.floor("h")
    weather_hourly = (
        weather.groupby("slot_ts")
        .agg(
            temperature_2m=("temperature_2m", "mean"),
            rain_mm=("rain", "mean"),
            weather_code=("weather_code", lambda x: x.mode().iloc[0] if not x.mode().empty else None),
        )
        .reset_index()
    )
    weather_hourly["is_raining"] = weather_hourly["rain_mm"] >= 0.1

    def temp_class(t: float) -> str:
        if t < 10:
            return "cold"
        if t < 20:
            return "mid"
        if t < 28:
            return "warm"
        return "hot"

    weather_hourly["temp_class"] = weather_hourly["temperature_2m"].apply(temp_class)

    agg = (
        agg.merge(stations, on="station_id", how="left")
        .merge(weather_hourly, on="slot_ts", how="left")
    )

    season_map = {12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring", 5: "Spring", 6: "Summer", 7: "Summer", 8: "Summer", 9: "Fall", 10: "Fall", 11: "Fall"}
    agg["season"] = agg["slot_ts"].dt.month.map(season_map)
    logging.info("Computed %s aggregate rows", len(agg))
    return agg


def get_latest_slot_ts(conn) -> Optional[datetime]:
    """Return the most recent slot timestamp in ``station_weather``."""
    sql = "SELECT MAX(slot_ts) FROM public.station_weather;"
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
        ts = row[0] if row and row[0] is not None else None
        logging.info("Latest processed slot_ts: %s", ts)
        return ts




def save_weather(df: pd.DataFrame, conn) -> None:
    """Save aggregated data into ``station_weather`` table."""
    create_sql = """
        CREATE TABLE IF NOT EXISTS public.station_weather (
            slot_ts TIMESTAMP,
            station_id INTEGER,
            bikes_taken INTEGER,
            bikes_returned INTEGER,
            lat DOUBLE PRECISION,
            lon DOUBLE PRECISION,
            cluster_id INTEGER,
            temperature_2m REAL,
            temp_class TEXT,
            rain_mm REAL,
            is_raining BOOLEAN,
            weather_code INTEGER,
            season TEXT,
            PRIMARY KEY (slot_ts, station_id)
        );
    """
    insert_sql = """
        INSERT INTO public.station_weather (
            slot_ts, station_id, bikes_taken, bikes_returned,
            lat, lon, cluster_id,
            temperature_2m, temp_class, rain_mm,
            is_raining, weather_code, season
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s
        )
        ON CONFLICT (slot_ts, station_id) DO UPDATE SET
            bikes_taken=EXCLUDED.bikes_taken,
            bikes_returned=EXCLUDED.bikes_returned,
            lat=EXCLUDED.lat,
            lon=EXCLUDED.lon,
            cluster_id=EXCLUDED.cluster_id,
            temperature_2m=EXCLUDED.temperature_2m,
            temp_class=EXCLUDED.temp_class,
            rain_mm=EXCLUDED.rain_mm,
            is_raining=EXCLUDED.is_raining,
            weather_code=EXCLUDED.weather_code,
            season=EXCLUDED.season;
    """
    with conn.cursor() as cur:
        cur.execute(create_sql)
        for row in df.itertuples(index=False):
            cur.execute(
                insert_sql,
                (
                    row.slot_ts,
                    row.station_id,
                    row.bikes_taken,
                    row.bikes_returned,
                    row.lat,
                    row.lon,
                    row.cluster_id,
                    row.temperature_2m,
                    row.temp_class,
                    row.rain_mm,
                    row.is_raining,
                    row.weather_code,
                    row.season,
                ),
            )
        conn.commit()
    logging.info("Inserted %s rows into station_weather", len(df))


def main() -> None:
    """CLI entry point."""
    logging.info("Weather ingestion started")
    with open_connection() as conn:
        last_ts = get_latest_slot_ts(conn)
        trips = load_trips(conn, since=last_ts, limit=TRIP_BATCH_SIZE)
        if trips.empty:
            logging.info("No new trips found")
            return
        weather = fetch_weather(trips)
        agg = compute_aggregates(trips, weather)
        save_weather(agg, conn)
    logging.info("Weather ingestion finished")


if __name__ == "__main__":
    main()
