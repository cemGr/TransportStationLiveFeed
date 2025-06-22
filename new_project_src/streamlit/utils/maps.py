import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

from core.db import get_session
from new_project_src.models import Station, LiveStationStatus


def base_map(center: tuple[float, float], zoom: int = 14) -> folium.Map:
    return folium.Map(location=center, zoom_start=zoom, control_scale=True)

def add_station_marker(fmap, lat, lon, bikes, docks, name):
    color = "green" if bikes else "red"
    folium.CircleMarker(
        [lat, lon],
        radius=8,
        color=color,
        fill=True,
        fill_opacity=0.9,
        popup=f"{name}<br>Bikes: {bikes}<br>Docks: {docks}",
    ).add_to(fmap)

def show_map(fmap, height: int = 600, key: str | None = None):
    st_folium(fmap, width="100%", height=height, returned_objects=[], key=key)



def add_all_stations(fmap: folium.Map) -> None:
    """
    Plot every Metro-Bike station on the given folium map.
    Uses live status to colour the markers:
      • green  – ≥1 bike & online
      • red    – 0 bikes  or offline
    """
    with get_session() as s:
        rows = (
            s.query(
                Station.latitude,
                Station.longitude,
                Station.name,
                LiveStationStatus.num_bikes,
                LiveStationStatus.num_docks,
                LiveStationStatus.online,
            )
            .join(LiveStationStatus, LiveStationStatus.station_id == Station.station_id)
        ).all()

    cluster = MarkerCluster().add_to(fmap)

    for lat, lon, name, bikes, docks, online in rows:
        colour = "green" if online and bikes > 0 else "red"
        folium.CircleMarker(
            (lat, lon),
            radius=6,
            color=colour,
            fill=True,
            fill_opacity=0.9,
            popup=f"{name}<br>Bikes: {bikes}<br>Docks: {docks}",
        ).add_to(cluster)