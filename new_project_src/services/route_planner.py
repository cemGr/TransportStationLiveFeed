from __future__ import annotations

import math
import os
from typing import Any, Dict, List, Tuple

import openrouteservice as ors
from core.exceptions import (
    ErrorCode,
    NoBikeStationError,
    NoCreditsLeftError,
    NoDockStationError,
    RoutePlannerError,
    RoutingFailedError,
)
from new_project_src.models.location import Location
from new_project_src.models.route_plan import RoutePlan
from new_project_src.services.nearest_station_with_bikes import nearest_stations_with_bikes
from new_project_src.services.nearest_station_with_docks import nearest_stations_with_docks


class RoutePlanner:
    """
    Plans a complete walk→bike→walk route.
    Returns a RoutePlan on success or raises a RoutePlannerError
    on failure.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("ORS_API_KEY")
        if not self.api_key:
            raise RuntimeError("ORS_API_KEY not set")
        self.client = ors.Client(key=self.api_key)

    def _route(self, coords: List[List[float]], profile: str) -> Dict[str, Any]:
        return self.client.directions(coords, profile=profile, format="geojson", radiuses=[-1, -1])

    @staticmethod
    def _summary(geojson: Dict[str, Any]) -> Tuple[float, float]:
        summary = geojson["features"][0]["properties"]["summary"]
        return float(summary["distance"]), float(summary["duration"])

    def _credits_remaining(self) -> int | None:
        if hasattr(self.client, "requester") and hasattr(self.client.requester, "rate_limits"):
            rl = self.client.requester.rate_limits() or {}
            if "remaining" in rl:
                return int(rl["remaining"])

        return None

    def _prime_headers(self, start: list[float], dest: list[float]) -> None:
        if self._credits_remaining() is None:
            _ = self._route([start, dest], profile="foot-walking")  # costs 1 credit

    @staticmethod
    def _max_k_for_credits(current_credits: int) -> int:
        # Each station pair needs 3 requests; combinations: k² * 3
        return max(int(math.floor(math.sqrt(max(current_credits // 3, 1)))), 1)

    # ────────────────────────────────────────────────────────── step 1: stations
    @staticmethod
    def _fetch_nearby_stations(
        starting_location: Location,
        destination: Location,
        k: int,
        stations_with_missing_live_data: bool = False,
    ) -> Tuple[List[Any], List[Any]]:
        """Return k nearest bike-out and dock-in stations or raise."""
        origins = nearest_stations_with_bikes(
            starting_location,
            k,
            stations_with_missing_live_data
        )
        if not origins:
            raise NoBikeStationError()

        docks = nearest_stations_with_docks(
            destination,
            k,
            stations_with_missing_live_data
        )
        if not docks:
            raise NoDockStationError()

        return origins, docks

    # ──────────────────────────────────────────────────────── step 2: credits
    def _adjust_for_credits(
        self,
        origins: List[Any],
        docks: List[Any],
        starting_location: Location,
        destination: Location,
    ) -> Tuple[List[Any], List[Any]]:
        """
        Ensure sufficient ORS credits are available.
        Might shrink the station lists or raise NoCreditsLeftError.
        """
        start_coords = [starting_location.longitude, starting_location.latitude]
        dest_coords = [destination.longitude, destination.latitude]
        self._prime_headers(start_coords, dest_coords)

        remaining = self._credits_remaining()
        if remaining is None:
            return origins, docks

        max_k = self._max_k_for_credits(remaining)
        if max_k < 1:
            raise NoCreditsLeftError()

        # limit both lists to available credit-derived k
        origins = origins[:max_k]
        docks = docks[:max_k]
        return origins, docks

    # ────────────────────────────────────────────────── step 3: combinations
    def _evaluate_combinations(
        self,
        origins: List[Any],
        docks: List[Any],
        starting_location: Location,
        destination: Location,
    ) -> RoutePlan:
        """Compute every origin/dock pair, return the best RoutePlan or raise."""
        best_duration = float("inf")
        result = RoutePlan()

        start_coords = [starting_location.longitude, starting_location.latitude]
        dest_coords = [destination.longitude, destination.latitude]

        for origin in origins:
            origin_coords = [origin.longitude, origin.latitude]
            for dock in docks:
                dock_coords = [dock.longitude, dock.latitude]

                walk1 = self._route(
                    [start_coords, origin_coords],
                    profile="foot-walking",
                )
                bike = self._route(
                    [origin_coords, dock_coords],
                    profile="cycling-regular",
                )
                walk2 = self._route(
                    [dock_coords, dest_coords],
                    profile="foot-walking",
                )

                d1, t1 = self._summary(walk1)
                d2, t2 = self._summary(bike)
                d3, t3 = self._summary(walk2)
                duration = t1 + t2 + t3

                if duration < best_duration:
                    best_duration = duration
                    result.origin_station = origin
                    result.dock_station = dock
                    result.walk_to_bike = walk1
                    result.bike_route = bike
                    result.walk_to_dest = walk2
                    result.total_distance_m = d1 + d2 + d3
                    result.total_duration_s = duration

        if result.origin_station is None:
            raise RoutingFailedError("Could not calculate any route")

        return result

    def plan(
        self,
        starting_location: Location,
        destination: Location,
        k: int = 3,
        stations_with_missing_live_data: bool = False,
    ) -> RoutePlan:
        """
        Public API: returns a complete RoutePlan or raises a RoutePlannerError.
        """
        try:
            origins, docks = self._fetch_nearby_stations(starting_location, destination, k, stations_with_missing_live_data)
            origins, docks = self._adjust_for_credits(
                origins, docks, starting_location, destination
            )
            return self._evaluate_combinations(
                origins, docks, starting_location, destination
            )

        except RoutePlannerError:
            raise
        except Exception as exc:
            raise RoutePlannerError(ErrorCode.INTERNAL, str(exc)) from exc
