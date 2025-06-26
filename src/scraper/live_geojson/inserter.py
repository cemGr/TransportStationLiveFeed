from pathlib import Path
import json

from sqlalchemy import or_, func
from sqlalchemy.dialects.postgresql import insert
from core.db import get_session
from src.models.live_station import LiveStationStatus
from src.models.station      import Station

class LiveGeoJSONInserter:
    def __init__(self, clean_json: Path):
        self.clean_json = clean_json

    def upsert(self) -> int:
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
            known = {
                id_ for (id_,) in session.query(Station.station_id).all()
            }

            rows = [r for r in raw_rows if r["station_id"] in known]
            if not rows:
                print("⚠️ No matching station_ids found in static table; skipping upsert")
                return 0

            # ---------- DEBUG: fetch current snapshot & print diffs ----------
            if True:
                old_rows = {
                    s.station_id: s
                    for s in session.query(LiveStationStatus)
                                    .filter(LiveStationStatus.station_id.in_([r["station_id"] for r in rows]))
                }
                for r in rows:
                    diff_line = self._diff(old_rows.get(r["station_id"]), r)
                    if diff_line:
                        print(diff_line)
            # -----------------------------------------------------------------

            stmt = insert(LiveStationStatus).values(rows)
            update_cols = {c.name: c for c in stmt.excluded
                           if c.name not in ("station_id",)}
            update_cols["updated_at"] = func.now()

            stmt = stmt.on_conflict_do_update(
                index_elements=[LiveStationStatus.station_id],
                set_=update_cols,
                where=or_(
                    LiveStationStatus.num_bikes.is_distinct_from(stmt.excluded.num_bikes),
                    LiveStationStatus.num_docks.is_distinct_from(stmt.excluded.num_docks),
                    LiveStationStatus.online.is_distinct_from(stmt.excluded.online),
                )
            )
            result = session.execute(stmt)
            count = result.rowcount or 0
            print(f"✅ upserted {count} live-status rows")
            return count

    def _diff(self, old, new) -> str | None:
        if old is None:
            return f"+ INSERT {new['station_id']}: {new}"
        changes = {
            k: (getattr(old, k), new[k])
            for k in ("num_bikes", "num_docks", "online")
            if getattr(old, k) != new[k]
        }
        return f"~ UPDATE {new['station_id']}: {changes}" if changes else None