import json
from pathlib import Path
from unittest.mock import MagicMock

from src.db.loaders import upsert_stations_from_json, insert_trips_from_csv


def sample_geojson(tmp_path: Path) -> Path:
    data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [13.0, 52.0]},
                "properties": {
                    "kioskId": 1,
                    "name": "A",
                    "bikesAvailable": 2,
                    "docksAvailable": 3,
                    "kioskPublicStatus": "Active",
                },
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [13.1, 52.1]},
                "properties": {
                    "kioskId": 2,
                    "name": "B",
                    "bikesAvailable": 1,
                    "docksAvailable": 4,
                    "kioskPublicStatus": "Inactive",
                },
            },
        ],
    }
    path = tmp_path / "stations.json"
    path.write_text(json.dumps(data))
    return path


def test_upsert_executes_insert(tmp_path):
    path = sample_geojson(tmp_path)
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur

    upsert_stations_from_json(path, conn)

    assert cur.execute.call_count == 2
    sql = cur.execute.call_args_list[0][0][0]
    assert "INSERT INTO public.stations" in sql
    assert "ON CONFLICT (station_id)" in sql
    conn.commit.assert_called_once()


def sample_trip_csv(tmp_path: Path) -> Path:
    data = (
        "duration,start_time,end_time,start_station,start_lat,start_lon,"\
        "end_station,end_lat,end_lon,bike_id,bike_type\n"
        "5,2024-01-01 00:00:00,2024-01-01 00:05:00,1,52.0,13.0,2,52.1,13.1,100,standard\n"
    )
    path = tmp_path / "trips.csv"
    path.write_text(data)
    return path


def sample_trip_csv_non_numeric(tmp_path: Path) -> Path:
    data = (
        "duration,start_time,end_time,start_station,start_lat,start_lon,"
        "end_station,end_lat,end_lon,bike_id,bike_type\n"
        "5,2024-01-01 00:00:00,2024-01-01 00:05:00,1,52.0,13.0,2,52.1,13.1,15316a,standard\n"
    )
    path = tmp_path / "trips_bad.csv"
    path.write_text(data)
    return path


def test_insert_trips_executes_insert(tmp_path):
    path = sample_trip_csv(tmp_path)
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur

    insert_trips_from_csv(path, conn)

    cur.execute.assert_called()
    sql = cur.execute.call_args_list[0][0][0]
    assert "INSERT INTO public.trips" in sql
    conn.commit.assert_called_once()


def test_insert_trips_handles_non_numeric_bike_id(tmp_path):
    path = sample_trip_csv_non_numeric(tmp_path)
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur

    insert_trips_from_csv(path, conn)

    args = cur.execute.call_args_list[0][0][1]
    assert args[9] is None
