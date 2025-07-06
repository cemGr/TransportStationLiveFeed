from __future__ import annotations
from domain.repositories import StationRepository
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely.strtree import STRtree
import numpy as np

def find_nearest_stations(
    repo: StationRepository, latitude: float, longitude: float, k: int = 5
):
    """Return nearest stations via the provided repository."""
    return repo.nearest_stations(latitude, longitude, k)


def find_nearest_docks(
    repo: StationRepository, latitude: float, longitude: float, k: int = 5
):
    """Return nearest docks via the provided repository."""
    return repo.nearest_docks(latitude, longitude, k)



def find_k_nearest_stations(
    stations_df: pd.DataFrame,
    start_lat: float,
    start_long: float,
    k: int,
    src_crs: str = "EPSG:4326",
    dst_crs: str = "EPSG:3857",
) -> pd.DataFrame:
    """Return the ``k`` nearest stations using an in-memory ``STRtree``."""

    gdf_m = gpd.GeoDataFrame(
        stations_df.copy(),
        geometry=gpd.points_from_xy(
            stations_df["start_long"], stations_df["start_lat"]
        ),
        crs=src_crs,
    ).to_crs(dst_crs)

    geoms = list(gdf_m.geometry)
    names = list(gdf_m["StationName"])
    lats = list(stations_df["start_lat"])
    longs = list(stations_df["start_long"])

    inp = (
        gpd.GeoSeries([Point(start_long, start_lat)], crs=src_crs)
        .to_crs(dst_crs)
        .iloc[0]
    )

    nearest = []
    for _ in range(min(k, len(geoms))):
        tree = STRtree(geoms)
        idx = tree.nearest(inp)
        if isinstance(idx, (list, tuple, np.ndarray)):
            idx = int(np.array(idx).flat[0])
        else:
            idx = int(idx)
        nearest.append((geoms[idx], names[idx], lats[idx], longs[idx]))
        geoms.pop(idx)
        names.pop(idx)
        lats.pop(idx)
        longs.pop(idx)

    return pd.DataFrame(
        {
            "StationName": [name for _, name, _, _ in nearest],
            "start_lat": [lat for _, _, lat, _ in nearest],
            "start_long": [lon for _, _, _, lon in nearest],
            "distance": [geom.distance(inp) for geom, _, _, _ in nearest],
        }
    )
