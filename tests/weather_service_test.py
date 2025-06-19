import pandas as pd
from unittest.mock import MagicMock, patch

import src.weather_service as ws


def sample_trips():
    return pd.DataFrame(
        {
            "start_time": [pd.Timestamp("2024-01-01 00:10:00")],
            "end_time": [pd.Timestamp("2024-01-01 00:15:00")],
            "start_station": [1],
            "end_station": [2],
            "start_lat": [52.0],
            "start_lon": [13.0],
            "end_lat": [52.1],
            "end_lon": [13.1],
        }
    )


def mock_weather_json():
    return [
        {
            "latitude": 52.0,
            "longitude": 13.0,
            "hourly": {
                "time": ["2024-01-01T00:00"],
                "temperature_2m": [10.0],
                "rain": [0.0],
                "weathercode": [1],
            },
        }
    ]


@patch("src.weather_service.open_connection")
@patch("src.weather_service.requests_cache.CachedSession")
@patch("src.weather_service.load_trips")
def test_main_inserts_weather(load_trips, cached_session, open_conn):
    load_trips.return_value = sample_trips()

    session = MagicMock()
    resp = MagicMock()
    resp.json.return_value = mock_weather_json()
    resp.raise_for_status = lambda: None
    session.get.return_value = resp
    cached_session.return_value = session

    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    open_conn.return_value.__enter__.return_value = conn

    ws.main()

    executed = "".join(call[0][0] for call in cur.execute.call_args_list)
    assert "INSERT INTO public.station_weather" in executed
