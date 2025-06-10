from psycopg2.extras import RealDictCursor

SQL_NEAREST_STATIONS = """
WITH user_location AS (
    SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326)::GEOGRAPHY AS geom
)
SELECT
    s.station_id,
    s.name,
    s.num_bikes,
    s.num_docks,
    s.online,
    ST_Distance(s.geom, u.geom) AS distance_m
FROM public.stations AS s
CROSS JOIN user_location AS u
WHERE s.num_bikes > 0 AND s.online = TRUE
ORDER BY s.geom <-> u.geom
LIMIT %s;
"""


SQL_NEAREST_DOCKS = """
WITH user_location AS (
    SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326)::GEOGRAPHY AS geom
)
SELECT
    s.station_id,
    s.name,
    s.num_bikes,
    s.num_docks,
    s.online,
    ST_Distance(s.geom, u.geom) AS distance_m
FROM public.stations AS s
CROSS JOIN user_location AS u
WHERE s.num_docks > 0 AND s.online = TRUE
ORDER BY s.geom <-> u.geom
LIMIT %s;
"""


def nearest_stations(conn, latitude: float, longitude: float, k: int = 5):
    """Execute k-NN station search using an existing connection."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(SQL_NEAREST_STATIONS, (longitude, latitude, k))
        return cur.fetchall()

def nearest_docks(conn, latitude: float, longitude: float, k: int = 5):
    """Execute k-NN station search using an existing connection."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(SQL_NEAREST_DOCKS, (longitude, latitude, k))
        return cur.fetchall()
