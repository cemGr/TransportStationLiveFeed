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
    """
    Finde die k nächsten Stationen zu einem Eingabepunkt, anhand von STRtree.

    Parameters
    ----------
    stations_df : pd.DataFrame
        DataFrame mit Spalten ['StationName', 'start_lat', 'start_long'].
    start_lat : float
        Breitengrad des Eingabepunkts.
    start_long : float
        Längengrad des Eingabepunkts.
    k : int
        Anzahl der nächsten Stationen, die zurückgegeben werden.
    src_crs : str
        CRS der Eingabekoordinaten (Standard WGS84).
    dst_crs : str
        Projektives CRS für metrische Entfernungen (Standard Web-Mercator).

    Returns
    -------
    pd.DataFrame
        DataFrame mit den Spalten ['StationName', 'start_lat', 'start_long',
        'distance'], sortiert nach aufsteigender Entfernung in Metern.
    """
    # 1) GeoDataFrame erstellen und ins metrische CRS transformieren
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

    # 2) Listen für STRtree und Namen
    geoms = list(gdf_m.geometry)
    names = list(gdf_m["StationName"])
    lats = list(stations_df["start_lat"])
    longs = list(stations_df["start_long"])

    # 3) Eingabepunkt in dieselbe Projektion
    inp = (
        gpd.GeoSeries([Point(start_long, start_lat)], crs=src_crs)
        .to_crs(dst_crs)
        .iloc[0]
    )

    # 4) Iteratives Nearest: pro Runde Baum bauen, Index ermitteln, aufnehmen & entfernen
    nearest = []
    for _ in range(min(k, len(geoms))):
        tree = STRtree(geoms)
        idx = tree.nearest(inp)
        # falls numpy-Array o.ä., erstes Element extrahieren
        if isinstance(idx, (list, tuple, np.ndarray)):
            idx = int(np.array(idx).flat[0])
        else:
            idx = int(idx)
        nearest.append((geoms[idx], names[idx], lats[idx], longs[idx]))
        # diese Station herausnehmen
        geoms.pop(idx)
        names.pop(idx)
        lats.pop(idx)
        longs.pop(idx)

    # 5) Ergebnis-DataFrame zusammenbauen
    result = pd.DataFrame({
        "StationName": [name for _, name, _, _ in nearest],
        "start_lat": [lat for _, _, lat, _ in nearest],
        "start_long": [lon for _, _, _, lon in nearest],
        "distance":    [geom.distance(inp) for geom, _, _, _ in nearest]
    })
    return result
