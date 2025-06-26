# src/scraper/weather/scraper.py
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import List, Tuple

import pandas as pd
from sqlalchemy import select, update, func

from core.db import get_session
from src.bikemetro.constants import BATCH_SIZE, MAX_SPAN_DAYS
from src.models.trip import Trip
from src.models.weather import StationWeather
from src.models.weather_checkpoint import WeatherCheckpoint
from src.scraper.weather.fetcher import WeatherFetcher
from src.scraper.weather.aggregator import WeatherAggregator
from src.scraper.weather.inserter import WeatherInserter

CHK_ID: bool = True


class WeatherScraper:
    def run_once(self) -> None:
        print("[WeatherScraper] run_once()")

        last_coord_idx = self._load_checkpoint()
        trips_df = self._get_new_trips()
        if trips_df is None:
            return

        coords = self._make_coord_list(trips_df)
        self._iterate_batches(trips_df, coords, last_coord_idx)
        self._reset_checkpoint()
        print("[WeatherScraper] 🎉 run_once() complete")


    @staticmethod
    def _load_checkpoint() -> int:
        with get_session() as session:
            idx = session.scalar(
                select(WeatherCheckpoint.last_coord_index)
                .where(WeatherCheckpoint.id == CHK_ID)
            )
            if idx is None:
                session.add(WeatherCheckpoint(id=CHK_ID, last_coord_index=0))
                session.commit()
                idx = 0
                print("[WeatherScraper] created checkpoint (idx=0)")
            else:
                print(f"[WeatherScraper] resume from coord idx {idx}")
        return idx

    @staticmethod
    def _save_checkpoint(next_idx: int) -> None:
        with get_session() as session:
            session.execute(
                update(WeatherCheckpoint)
                .where(WeatherCheckpoint.id == CHK_ID)
                .values(last_coord_index=next_idx, updated_at=func.now())
            )
            session.commit()
        print(f"[WeatherScraper] checkpoint → {next_idx}")

    @staticmethod
    def _reset_checkpoint() -> None:
        WeatherScraper._save_checkpoint(0)
        print("[WeatherScraper] ✅ checkpoint reset to 0")


    @staticmethod
    def _get_new_trips() -> pd.DataFrame | None:
        with get_session() as session:
            last_ts = session.scalar(select(func.max(StationWeather.slot_ts)))
            print(f"[WeatherScraper] Last weather slot_ts in DB: {last_ts}")

            stmt = select(
                Trip.start_time, Trip.end_time,
                Trip.start_station, Trip.start_lat, Trip.start_lon,
                Trip.end_station, Trip.end_lat, Trip.end_lon,
            )
            if last_ts:
                stmt = stmt.where(Trip.start_time > last_ts)
            rows = session.execute(stmt).mappings().all()

        if not rows:
            print("[WeatherScraper] No new trips – nothing to do")
            return None

        df = pd.DataFrame(rows)
        print("[WeatherScraper] trips_df shape:", df.shape)
        return df


    @staticmethod
    def _make_coord_list(trips_df: pd.DataFrame) -> List[Tuple[float, float]]:
        coords = (
            trips_df[["start_lat", "start_lon"]]
            .drop_duplicates()
            .sort_values(["start_lat", "start_lon"])
            .itertuples(index=False, name=None)
        )
        coords = list(coords)
        print(f"[WeatherScraper] unique coords: {len(coords)}")
        return coords


    def _iterate_batches(
            self,
            trips_df: pd.DataFrame,
            coords: List[Tuple[float, float]],
            start_idx: int,
    ) -> None:
        total_batches = math.ceil(len(coords) / BATCH_SIZE)

        for bi in range(start_idx, len(coords), BATCH_SIZE):
            coord_batch = coords[bi: bi + BATCH_SIZE]
            batch_no = bi // BATCH_SIZE + 1
            print(f"[WeatherScraper] ── Batch {batch_no}/{total_batches} "
                  f"({len(coord_batch)} coords)")

            trips_b = trips_df.merge(
                pd.DataFrame(coord_batch, columns=["start_lat", "start_lon"]),
                on=["start_lat", "start_lon"],
                how="inner",
            )
            if trips_b.empty:
                print("[WeatherScraper]    no trips in this batch")
            else:
                ok = self._process_windows(trips_b)
                if not ok:
                    return

            self._save_checkpoint(bi + BATCH_SIZE)


    def _process_windows(self, trips_b: pd.DataFrame) -> bool:
        start_d: date = trips_b["start_time"].min().date()
        end_d: date = trips_b["start_time"].max().date()
        span = timedelta(days=MAX_SPAN_DAYS - 1)
        cur_d = start_d

        while cur_d <= end_d:
            win_end = min(cur_d + span, end_d)
            mask = (trips_b["start_time"].dt.date >= cur_d) & \
                   (trips_b["start_time"].dt.date <= win_end)
            trips_w = trips_b[mask]
            if trips_w.empty:
                cur_d = win_end + timedelta(days=1)
                continue

            print(f"[WeatherScraper] Window {cur_d} → {win_end} "
                  f"· trips {len(trips_w)}")

            if not self._process_window(trips_w):
                return False
            cur_d = win_end + timedelta(days=1)

        return True

    @staticmethod
    def _process_window(trips_w: pd.DataFrame) -> bool:
        weather_df = WeatherFetcher(trips_w).fetch()
        if weather_df.empty:
            print("[WeatherScraper] ⚠️ empty weather – stopping run")
            return False

        agg_df = WeatherAggregator.aggregate(trips_w, weather_df)
        inserted = WeatherInserter(agg_df).upsert()
        print(f"[WeatherScraper] ✅ upserted {inserted} rows")
        return True

# class WeatherScraper:
#     """
#     Incremental version:
#     ┌─────────────┐   ┌───────────────┐   ┌───────────────┐
#     │ trips batch │ → │ weather fetch │ → │  aggregate &  │
#     │  (≤BATCH)   │   │   (≤14 days)  │   │   upsert      │
#     └─────────────┘   └───────────────┘   └───────────────┘
#     and repeat until the API or the data is exhausted.
#     """
#
#     # ------------------------------------------------------------------
#     def __init__(self) -> None:
#         print("[WeatherScraper] ⚙️  Instance created (incremental)")
#
#     # ------------------------------------------------------------------
#     def run_once(self) -> None:
#         print("[WeatherScraper] ▶️  run_once()")
#
#         # 1. pull all trips newer than the latest weather slot already stored
#         with get_session() as session:
#             last_ts = session.scalar(select(func.max(StationWeather.slot_ts)))
#             print(f"[WeatherScraper] Last weather slot_ts in DB: {last_ts}")
#
#             stmt = select(
#                 Trip.start_time, Trip.end_time,
#                 Trip.start_station, Trip.start_lat, Trip.start_lon,
#                 Trip.end_station,   Trip.end_lat,   Trip.end_lon,
#             )
#             if last_ts:
#                 stmt = stmt.where(Trip.start_time > last_ts)
#
#             trips = session.execute(stmt).mappings().all()
#
#         if not trips:
#             print("[WeatherScraper] ℹ️  No new trips")
#             return
#
#         trips_df = pd.DataFrame(trips)
#         print("[WeatherScraper] 🚲 trips_df shape:", trips_df.shape)
#
#         # 2. derive coordinate batches once
#         coords = (
#             trips_df[["start_lat", "start_lon"]]
#             .drop_duplicates()
#             .itertuples(index=False, name=None)
#         )
#         coords = list(coords)
#         print(f"[WeatherScraper] 🌍 unique coords: {len(coords)}")
#
#         # 3. outer loop over coordinate batches
#         for bi in range(0, len(coords), BATCH_SIZE):
#             coord_batch = coords[bi : bi + BATCH_SIZE]
#             print(f"[WeatherScraper] ── Batch {bi // BATCH_SIZE + 1} / "
#                   f"{(len(coords) + BATCH_SIZE - 1)//BATCH_SIZE} "
#                   f"({len(coord_batch)} coords)")
#
#             # slice trips for *this* batch to keep aggregations small
#             trips_b = trips_df.merge(
#                 pd.DataFrame(coord_batch, columns=["start_lat", "start_lon"]),
#                 on=["start_lat", "start_lon"],
#                 how="inner",
#             )
#             if trips_b.empty:
#                 print("[WeatherScraper]    🤷  Batch has no matching trips, skip")
#                 continue
#
#             # 4. inner loop over 14-day windows
#             start_date = trips_b["start_time"].min().date()
#             end_date   = trips_b["start_time"].max().date()
#             span       = timedelta(days=MAX_SPAN_DAYS - 1)
#             cur_date   = start_date
#
#             while cur_date <= end_date:
#                 win_end = min(cur_date + span, end_date)
#                 mask = (trips_b["start_time"].dt.date >= cur_date) & \
#                        (trips_b["start_time"].dt.date <= win_end)
#                 trips_w = trips_b[mask]
#
#                 if trips_w.empty:
#                     cur_date = win_end + timedelta(days=1)
#                     continue
#
#                 print(f"[WeatherScraper]    📆 Window {cur_date} → {win_end} "
#                       f"· trips {len(trips_w)}")
#
#                 # --- fetch, aggregate, upsert ---------------------------
#                 weather_df = WeatherFetcher(trips_w).fetch()
#
#                 if weather_df.empty:
#                     print("[WeatherScraper]       ⚠️  No weather data returned")
#                     break  # API quota probably hit; bail out early
#
#                 agg_df = WeatherAggregator.aggregate(trips_w, weather_df)
#                 inserted = WeatherInserter(agg_df).upsert()
#
#                 print(f"[WeatherScraper]       ✓ upserted {inserted} rows "
#                       f"for this window")
#
#                 # move to next window
#                 cur_date = win_end + timedelta(days=1)
#
#                 # optional: quit early for the day if you’re near the quota
#                 # if inserted == 0:
#                 #     print("[WeatherScraper]       🛑  Stopping – quota likely hit")
#                 #     return
#
#         print("[WeatherScraper] 🎉 run_once() complete")
