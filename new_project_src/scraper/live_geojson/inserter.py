from pathlib import Path
import json

from sqlalchemy.dialects.postgresql import insert
from core.db import get_session
from new_project_src.models.live_station import LiveStationStatus
from new_project_src.models.station      import Station

class LiveGeoJSONInserter:
    """
    Upsert every feature in the cleaned GeoJSON into live_station_status,
    but only for station_ids that already exist in the static stations table.
    """
    def __init__(self, clean_json: Path):
        self.clean_json = clean_json

    def upsert(self) -> int:
        # 1) load features
        data = json.loads(self.clean_json.read_text(encoding="utf-8"))
        raw_rows = []
        for feat in data.get("features", []):
            props = feat.get("properties", {})
            station_id = props.get("kioskId") or props.get("station_id")
            raw_rows.append({
                "station_id": station_id,
                "num_bikes" : props.get("bikesAvailable", 0),
                "num_docks" : props.get("docksAvailable") or props.get("totalDocks", 0),
                "online"    : str(props.get("kioskPublicStatus", "")).lower() == "active",
            })

        with get_session() as session:
            # 2) fetch all known station_ids
            known = {
                id_ for (id_,) in session.query(Station.station_id).all()
            }

            # 3) filter out any unknown kiosks
            rows = [r for r in raw_rows if r["station_id"] in known]
            if not rows:
                print("⚠ No matching station_ids found in static table; skipping upsert")
                return 0

            # 4) bulk upsert
            stmt = insert(LiveStationStatus).values(rows)
            update_cols = {
                c.name: c
                for c in stmt.excluded
                if c.name not in ("station_id", "updated_at")
            }
            stmt = stmt.on_conflict_do_update(
                index_elements=[LiveStationStatus.station_id],
                set_=update_cols
            )
            result = session.execute(stmt)
            count = result.rowcount or 0
            print(f"✓ upserted {count} live-status rows")
            return count
