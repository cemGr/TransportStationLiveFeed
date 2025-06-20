# file: spatial_utils.py

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely.strtree import STRtree
import numpy as np

def find_k_nearest_stations(
    stations_df: pd.DataFrame,
    start_lat: float,
    start_long: float,
    k: int,
    src_crs: str = "EPSG:4326",
    dst_crs: str = "EPSG:3857"
) -> pd.DataFrame:
    """Return the k nearest stations for a given point using ``STRtree``.

    Parameters
    ----------
    stations_df : pd.DataFrame
        DataFrame with columns ['StationName', 'start_lat', 'start_long'].
    start_lat : float
        Latitude of the input point.
    start_long : float
        Longitude of the input point.
    k : int
        Number of nearest stations to return.
    src_crs : str
        CRS of the input coordinates (default WGS84).
    dst_crs : str
        Projected CRS for metric distances (default Web-Mercator).

    Returns
    -------
    pd.DataFrame
        DataFrame with columns ['StationName', 'start_lat', 'start_long',
        'distance'] sorted by ascending distance in meters.
    """
    # 1) Create a GeoDataFrame and transform to a metric CRS
    gdf_m = (
        gpd.GeoDataFrame(
            stations_df.copy(),
            geometry=gpd.points_from_xy(
                stations_df["start_long"], stations_df["start_lat"]
            ),
            crs=src_crs
        )
        .to_crs(dst_crs)
    )

    # 2) Lists for STRtree and names
    geoms = list(gdf_m.geometry)
    names = list(gdf_m["StationName"])
    lats = list(stations_df["start_lat"])
    longs = list(stations_df["start_long"])

    # 3) Input point in the same projection
    inp = (
        gpd.GeoSeries([Point(start_long, start_lat)], crs=src_crs)
        .to_crs(dst_crs)
        .iloc[0]
    )

    # 4) Iteratively find the nearest station, then remove it
    nearest = []
    for _ in range(min(k, len(geoms))):
        tree = STRtree(geoms)
        idx = tree.nearest(inp)
        # ``nearest`` can return numpy arrays; take the first element
        if isinstance(idx, (list, tuple, np.ndarray)):
            idx = int(np.array(idx).flat[0])
        else:
            idx = int(idx)
        nearest.append((geoms[idx], names[idx], lats[idx], longs[idx]))
        # remove this station from consideration
        geoms.pop(idx)
        names.pop(idx)
        lats.pop(idx)
        longs.pop(idx)

    # 5) Build the result DataFrame
    result = pd.DataFrame({
        "StationName": [name for _, name, _, _ in nearest],
        "start_lat": [lat for _, _, lat, _ in nearest],
        "start_long": [lon for _, _, _, lon in nearest],
        "distance":    [geom.distance(inp) for geom, _, _, _ in nearest]
    })
    return result
