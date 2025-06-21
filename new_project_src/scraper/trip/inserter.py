from pathlib import Path
import pandas as pd

from core.db import get_session
from new_project_src.models.trip import Trip
from new_project_src.models.station import Station

class TripInserter:
    """
    Bulk-insert a cleaned trip CSV into Postgres, dropping any trips
    whose start or end station isn’t present in the static stations table.
    """

    def __init__(self, cleaned_csv: Path):
        self.cleaned = cleaned_csv

    def insert(self) -> int:
        df = pd.read_csv(self.cleaned)
        rows = df.to_dict("records")

        with get_session() as session:
            # fetch all valid station IDs
            known = {sid for (sid,) in session.query(Station.station_id).all()}

            # filter out any trips referencing unknown stations
            valid = [
                r for r in rows
                if r["start_station"] in known and r["end_station"] in known
            ]
            dropped = len(rows) - len(valid)
            if dropped:
                print(f"⚠ Dropped {dropped} trips with missing station references")

            # bulk insert only the valid trips
            session.bulk_insert_mappings(Trip, valid)
            return len(valid)