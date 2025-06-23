from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Sequence, Mapping

class StationRepository(ABC):
    """Abstraction for station data access."""

    @abstractmethod
    def nearest_stations(self, latitude: float, longitude: float, k: int = 5) -> Sequence[Mapping]:
        """Return ``k`` nearest stations with available bikes."""
        raise NotImplementedError

    @abstractmethod
    def nearest_docks(self, latitude: float, longitude: float, k: int = 5) -> Sequence[Mapping]:
        """Return ``k`` nearest stations with available docks."""
        raise NotImplementedError
