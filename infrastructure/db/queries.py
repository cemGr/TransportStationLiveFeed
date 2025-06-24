from psycopg2.extras import RealDictCursor


SQL_NEAREST_TEMPLATE = """
WITH user_location AS (
    SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326)::GEOGRAPHY AS geom
)
SELECT
    s.station_id,
    s.name,
    s.longitude,
    s.latitude,
    s.num_bikes,
    s.num_docks,
    s.online,
    ST_Distance(s.geom, u.geom) AS distance_m
FROM public.stations AS s
CROSS JOIN user_location AS u
WHERE {condition} AND s.online = TRUE
ORDER BY s.geom <-> u.geom
LIMIT %s;
"""


def _nearest(
    conn, latitude: float, longitude: float, k: int, condition: str
) -> list[dict]:
    """Execute the generic nearest station query."""
    sql = SQL_NEAREST_TEMPLATE.format(condition=condition)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, (longitude, latitude, k))
        return cur.fetchall()


def nearest_stations(conn, latitude: float, longitude: float, k: int = 5):
    """Return stations with available bikes ordered by distance."""
    return _nearest(conn, latitude, longitude, k, "s.num_bikes > 0")


def nearest_docks(conn, latitude: float, longitude: float, k: int = 5):
    """Return stations with free docks ordered by distance."""
    return _nearest(conn, latitude, longitude, k, "s.num_docks > 0")
