import os
import openrouteservice as ors
from new_project_src.services.nearest_station_with_bikes import nearest_stations_with_bikes
from new_project_src.services.nearest_station_with_docks import nearest_stations_with_docks

class RoutePlanner:
    """
    Plan a walk→bike→walk route using ORS.
    Origin and dock stations are returned as Station instances with .distance_m.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("ORS_API_KEY")
        if not self.api_key:
            raise RuntimeError("ORS_API_KEY not set")
        self.client = ors.Client(key=self.api_key)

    def plan(
        self,
        start_lat: float,
        start_lon: float,
        dest_lat: float,
        dest_lon: float,
        k: int = 5,
    ) -> dict:
        # 1) pick nearest bike station
        origins = nearest_stations_with_bikes(start_lat, start_lon, k)
        if not origins:
            raise ValueError("No nearby stations with available bikes")
        origin = origins[0]

        # 2) pick nearest dock station to destination
        docks = nearest_stations_with_docks(dest_lat, dest_lon, k)
        if not docks:
            raise ValueError("No nearby stations with free docks")
        dock = docks[0]

        # helper to fetch a GeoJSON route
        def _route(coords: list[list[float]], profile: str):
            return self.client.directions(coords, profile=profile, format="geojson")

        # 3) walk to bike, cycle, then walk to dest
        walk1 = _route(
            [[start_lon, start_lat], [origin.longitude, origin.latitude]],
            profile="foot-walking",
        )
        bike = _route(
            [[origin.longitude, origin.latitude],
             [dock.longitude,   dock.latitude]],
            profile="cycling-regular",
        )
        walk2 = _route(
            [[dock.longitude, dock.latitude], [dest_lon, dest_lat]],
            profile="foot-walking",
        )

        return {
            "origin_station": origin,
            "dock_station"  : dock,
            "walk_to_bike"  : walk1,
            "bike_route"    : bike,
            "walk_to_dest"  : walk2,
        }
