import json
import csv
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


def insert_trips_from_csv(path: Path, conn):
    """Insert cleaned trip CSV rows into the database."""

    sql = """
        INSERT INTO public.trips (
            duration,
            start_time,
            end_time,
            start_station,
            start_lat,
            start_lon,
            end_station,
            end_lat,
            end_lon,
            bike_id,
            bike_type
        ) VALUES (
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s
        );
    """

    with conn.cursor() as cur, open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cur.execute(
                sql,
                (
                    int(row.get("duration", 0)),
                    row.get("start_time"),
                    row.get("end_time"),
                    int(row.get("start_station", 0)),
                    float(row.get("start_lat", 0.0)),
                    float(row.get("start_lon", 0.0)),
                    int(row.get("end_station", 0)),
                    float(row.get("end_lat", 0.0)),
                    float(row.get("end_lon", 0.0)),
                    int(row.get("bike_id", 0)),
                    row.get("bike_type"),
                ),
            )
        conn.commit()
