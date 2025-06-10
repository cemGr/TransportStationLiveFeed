import json
from pathlib import Path
from unittest.mock import MagicMock

from src.db.loaders import upsert_stations_from_json


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
