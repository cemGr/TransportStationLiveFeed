import math
from sqlalchemy.dialects.postgresql import insert
from core.db import get_session
from src.models.weather import StationWeather

# ---- Postgres binding limits -----------------------------------------
MAX_BIND_PARAMS   = 65_000          # tiny safety margin
COLS_PER_ROW_INS  = 13              # all columns in VALUES(...)
COLS_PER_ROW_UPD  = 11              # columns updated in ON CONFLICT
COLS_PER_ROW      = COLS_PER_ROW_INS + COLS_PER_ROW_UPD

MAX_ROWS_PER_CHUNK = MAX_BIND_PARAMS // COLS_PER_ROW  # ≈ 2700
SAFE_CHUNK         = 2_500

class WeatherInserter:
    def __init__(self, agg_df):
        self.agg = agg_df.dropna(subset=["lat", "lon"])
        print("[WeatherInserter] agg_df after drop-na:", self.agg.shape)

    # ------------------------------------------------------------------
    def upsert(self) -> int:
        rows = self.agg.to_dict("records")
        chunk_sz = min(SAFE_CHUNK, MAX_ROWS_PER_CHUNK)
        n_chunks = math.ceil(len(rows) / chunk_sz)
        written  = 0

        with get_session() as session:
            for i in range(n_chunks):
                chunk = rows[i * chunk_sz : (i+1) * chunk_sz]
                if not chunk:
                    continue

                stmt = insert(StationWeather).values(chunk)
                upd_cols = {c.name: c for c in stmt.excluded
                            if c.name not in ("slot_ts", "station_id")}
                stmt = stmt.on_conflict_do_update(
                           index_elements=[StationWeather.slot_ts,
                                           StationWeather.station_id],
                           set_=upd_cols)

                res = session.execute(stmt)
                session.commit()
                written += res.rowcount or 0
                print(f"[WeatherInserter]    chunk {i+1}/{n_chunks}"
                      f" – {len(chunk)} rows")

        print(f"[WeatherInserter] ✅ total rows written: {written}")
        return written