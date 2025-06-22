from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(slots=True)
class RoutePlan:
    origin_station: Any | None = None
    dock_station: Any | None = None
    walk_to_bike: Dict[str, Any] | None = None
    bike_route: Dict[str, Any] | None = None
    walk_to_dest: Dict[str, Any] | None = None
    total_distance_m: float | None = None
    total_duration_s: float | None = None