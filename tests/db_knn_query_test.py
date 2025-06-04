from unittest.mock import MagicMock, patch
from src.db import query_nearest_stations


def test_query_nearest_executes_sql():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_cur.fetchall.return_value = [{"station_id": 1}]

    with patch("src.db.connection.psycopg2.connect", return_value=mock_conn) as connect:
        result = query_nearest_stations(52.5, 13.4, k=3)

    connect.assert_called_once()
    mock_cur.execute.assert_called_once()
    sql = mock_cur.execute.call_args[0][0]
    assert "ORDER BY s.geom <-> u.geom" in sql
    assert result == [{"station_id": 1}]
