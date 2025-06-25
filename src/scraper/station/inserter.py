import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from geoalchemy2 import WKTElement
from core.db import get_session
from src.models.station import Station

class StationInserter:
    def __init__(self, cleaned_csv_path):
        self.cleaned = cleaned_csv_path

    def upsert(self) -> int:
        df = pd.read_csv(self.cleaned, encoding="latin-1")
        rows = df.to_dict("records")

        with get_session() as session:
            stmt = insert(Station).values([
                dict(
                    station_id = r["Kiosk ID"],
                    name       = r["Kiosk Name"],
                    longitude  = r["Longitude"],
                    latitude   = r["Latitude"],
                    geom       = WKTElement(f"POINT({r['Longitude']} {r['Latitude']})", srid=4326)
                )
                for r in rows
            ])
            update_cols = {c.name: c for c in stmt.excluded if c.name not in ("station_id","geom")}
            stmt = stmt.on_conflict_do_update(index_elements=[Station.station_id], set_=update_cols)
            result = session.execute(stmt)
            return result.rowcount
