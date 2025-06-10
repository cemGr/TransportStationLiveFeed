import json
from pathlib import Path


def upsert_stations_from_json(path: Path, conn):
    """Insert or update stations from a GeoJSON snapshot."""
    data = json.loads(Path(path).read_text())
    features = data.get("features", [])

    sql = """
        INSERT INTO public.stations
          (station_id, name, longitude, latitude, num_bikes, num_docks, online, geom)
        VALUES (%s, %s, %s, %s, %s, %s, %s,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)::GEOGRAPHY)
        ON CONFLICT (station_id) DO UPDATE SET
          name = EXCLUDED.name,
          longitude = EXCLUDED.longitude,
          latitude = EXCLUDED.latitude,
          num_bikes = EXCLUDED.num_bikes,
          num_docks = EXCLUDED.num_docks,
          online = EXCLUDED.online,
          geom = EXCLUDED.geom;
    """

    with conn.cursor() as cur:
        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            lon, lat = geom.get("coordinates", (None, None))[:2]
            station_id = props.get("kioskId") or props.get("station_id")
            name = props.get("name")
            num_bikes = props.get("bikesAvailable")
            num_docks = props.get("docksAvailable") or props.get("totalDocks")
            online = str(props.get("kioskPublicStatus", "")).lower() == "active"

            cur.execute(
                sql,
                (
                    station_id,
                    name,
                    lon,
                    lat,
                    num_bikes,
                    num_docks,
                    online,
                    lon,
                    lat,
                ),
            )
        conn.commit()
