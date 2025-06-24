
import pandas as pd
from sqlalchemy import select, func

from core.db import get_session
from new_project_src.models.trip    import Trip
from new_project_src.models.weather import StationWeather

from new_project_src.scraper.weather.fetcher    import WeatherFetcher
from new_project_src.scraper.weather.aggregator import WeatherAggregator
from new_project_src.scraper.weather.inserter   import WeatherInserter

class WeatherScraper:
    def __init__(self):
        pass

    def run_once(self) -> None:
        with get_session() as session:
            last_ts = session.scalar(
                select(func.max(StationWeather.slot_ts))
            )

            stmt = select(
                Trip.start_time, Trip.end_time,
                Trip.start_station, Trip.start_lat, Trip.start_lon,
                Trip.end_station,   Trip.end_lat,   Trip.end_lon
            )
            if last_ts is not None:
                stmt = stmt.where(Trip.start_time > last_ts)

            trips = session.execute(stmt).mappings().all()

        if not trips:
            print("ℹ️ No new trips")
            return

        trips_df = pd.DataFrame(trips)

        weather_df = WeatherFetcher(trips_df).fetch()

        agg_df = WeatherAggregator.aggregate(trips_df, weather_df)

        count = WeatherInserter(agg_df).upsert()
        print(f"✓ Weather pipeline processed {len(trips_df)} trips → {count} rows upserted")

