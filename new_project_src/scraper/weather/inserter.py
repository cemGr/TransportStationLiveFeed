from pathlib import Path
import pandas as pd

from sqlalchemy.dialects.postgresql import insert
from core.db import get_session
from new_project_src.models.weather import StationWeather

class WeatherInserter:
    def __init__(self, agg_df: pd.DataFrame):
        self.agg = agg_df

    def upsert(self) -> int:
        rows = self.agg.to_dict("records")
        with get_session() as session:
            stmt = insert(StationWeather).values(rows)
            update_cols = {
                col.name: col
                for col in stmt.excluded
                if col.name not in ("slot_ts","station_id")
            }
            stmt = stmt.on_conflict_do_update(
                index_elements=[StationWeather.slot_ts, StationWeather.station_id],
                set_=update_cols
            )
            result = session.execute(stmt)
            return result.rowcount or 0
