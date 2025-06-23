from __future__ import annotations

from domain.repositories import StationRepository


def find_nearest_stations(repo: StationRepository, latitude: float, longitude: float, k: int = 5):
    """Return nearest stations via the provided repository."""
    return repo.nearest_stations(latitude, longitude, k)


def find_nearest_docks(repo: StationRepository, latitude: float, longitude: float, k: int = 5):
    """Return nearest docks via the provided repository."""
    return repo.nearest_docks(latitude, longitude, k)
