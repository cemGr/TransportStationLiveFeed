import folium
import streamlit as st
from new_project_src.models.location import Location
from new_project_src.services.nearest_station_with_bikes import (
    nearest_stations_with_bikes,
)
from new_project_src.streamlit.utils import widgets, maps

st.header("🔎 Find Nearest Bikes")

with st.form("find_bikes"):
    lat, lon = widgets.lat_lon_input("Your location", default=(34.0522, -118.2437))
    k = st.slider("Number of stations (K)", 1, 20, 5)
    submit = st.form_submit_button("Search")

if submit:
    loc = Location(latitude=lat, longitude=lon)
    stations = nearest_stations_with_bikes(loc, k)
    if not stations:
        st.error("No online stations with bikes found.")
    else:
        st.dataframe(
            {
                "Station": [s.name for s in stations],
                "Bikes":   [s.num_bikes for s in stations],
                "Distance (m)": [round(s.distance_m) for s in stations],
            },
            use_container_width=True,
        )

        # Map
        fmap = maps.base_map(center=(lat, lon))
        folium.Marker([lat, lon], tooltip="You").add_to(fmap)
        for s in stations:
            maps.add_station_marker(
                fmap, s.latitude, s.longitude, s.num_bikes, s.num_docks, s.name
            )
        maps.show_map(fmap, key="find_bikes_map")
