import folium
from streamlit_folium import st_folium



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