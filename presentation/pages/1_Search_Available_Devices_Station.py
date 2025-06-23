import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium

# ensure src package is resolvable when running with streamlit
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from infrastructure.db import query_nearest_stations

st.title("🚲 Available stations with bikes nearby")

if "nearest_bikes" not in st.session_state:
    st.session_state["nearest_bikes"] = None
    st.session_state["user_loc"] = None

with st.form("bike_search"):
    lat = st.number_input("Latitude", value=34.05, format="%.5f")
    lon = st.number_input("Longitude", value=-118.25, format="%.5f")
    k = st.number_input("Number of stations", min_value=1, value=5, step=1)
    submitted = st.form_submit_button("search")

if submitted:
    try:
        st.session_state["nearest_bikes"] = query_nearest_stations(
            latitude=lat, longitude=lon, k=int(k)
        )
        st.session_state["user_loc"] = (lat, lon)
    except Exception as e:  # pragma: no cover - UI feedback
        st.error(f"Database connection failed: {e}")

if st.session_state["nearest_bikes"]:
    lat, lon = st.session_state["user_loc"]
    result = st.session_state["nearest_bikes"]

    df = pd.DataFrame(result)
    df["distance_m"] = df["distance_m"].round(1)
    st.subheader("Available stations")
    st.table(df[["name", "num_bikes", "distance_m"]])

    m = folium.Map(location=[lat, lon], zoom_start=13)
    folium.Marker([lat, lon], tooltip="You", icon=folium.Icon(color="red")).add_to(m)
    for row in result:
        folium.Marker(
            [row["latitude"], row["longitude"]],
            tooltip=f"{row['name']} ({row['num_bikes']} Bikes)",
            icon=folium.Icon(color="blue"),
        ).add_to(m)

    st_folium(m, width=700, height=500)
