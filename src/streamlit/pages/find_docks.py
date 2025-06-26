import streamlit as st
import folium
from src.models.location import Location
from src.services.nearest_station_with_docks import (
    nearest_stations_with_docks,
)
from src.streamlit.utils import widgets, maps
st.header("Find Nearest Docks")

with st.form("find_docks"):
    lat, lon = widgets.lat_lon_input("Your current location", (34.0522, -118.2437))
    k = st.slider("Number of stations (K)", 1, 20, 5)
    submit = st.form_submit_button("Search")

if submit:
    loc = Location(latitude=lat, longitude=lon)
    stations = nearest_stations_with_docks(loc, k)

    if not stations:
        st.warning("No online stations with free docks found.")
        st.stop()

    st.dataframe(
        {
            "Station": [s.name for s in stations],
            "Free docks": [s.num_docks for s in stations],
            "Distance (m)": [round(s.distance_m) for s in stations],
        },
        use_container_width=True,
    )
    fmap = maps.base_map(center=(lat, lon))
    folium.Marker([lat, lon], tooltip="You").add_to(fmap)

    for s in stations:
        maps.add_station_marker(
            fmap,
            s.latitude,
            s.longitude,
            bikes=s.num_bikes,
            docks=s.num_docks,
            name=s.name,
        )

    maps.show_map(fmap, key="find_docks_map")
