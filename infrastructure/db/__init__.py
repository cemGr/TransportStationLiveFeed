from __future__ import annotations

from .connection import open_connection
from .queries import nearest_stations as _nearest_stations, nearest_docks as _nearest_docks
from .loaders import insert_trips_from_csv, upsert_stations_from_json
from domain.repositories import StationRepository

class DBStationRepository(StationRepository):
    """Station repository backed by PostgreSQL/PostGIS."""

    def __init__(self, connection=None):
        self.conn = connection or open_connection()

    def nearest_stations(self, latitude: float, longitude: float, k: int = 5):
        return _nearest_stations(self.conn, latitude, longitude, k)

    def nearest_docks(self, latitude: float, longitude: float, k: int = 5):
        return _nearest_docks(self.conn, latitude, longitude, k)

    def close(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


def query_nearest_stations(latitude: float, longitude: float, k: int = 5):
    """Convenience function using a temporary connection."""
    with DBStationRepository() as repo:
        return repo.nearest_stations(latitude, longitude, k)


def query_nearest_docks(latitude: float, longitude: float, k: int = 5):
    """Convenience function using a temporary connection."""
    with DBStationRepository() as repo:
        return repo.nearest_docks(latitude, longitude, k)
