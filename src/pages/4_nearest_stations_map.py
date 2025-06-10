import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# allow running this page directly
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.datastructure.rtree import find_k_nearest_stations

@st.cache_data
def load_stations():
    df = pd.read_csv("jupyter/cleaned_station_data.csv")
    df = df.rename(columns={"Kiosk Name": "StationName", "Latitude": "start_lat", "Longitude": "start_long"})
    df = df[df["Status"] == "Active"].reset_index(drop=True)
    return df[["StationName", "start_lat", "start_long"]]

st.title("🚏 Nächste Stationen finden")

if "nearest" not in st.session_state:
    st.session_state["nearest"] = None
    st.session_state["user_loc"] = None

with st.form("knn_form"):
    lat = st.number_input("Latitude", value=34.05, format="%.5f")
    lon = st.number_input("Longitude", value=-118.25, format="%.5f")
    k = st.number_input("Anzahl Stationen", min_value=1, value=5, step=1)
    submitted = st.form_submit_button("Suche")

if submitted:
    stations = load_stations()

    st.session_state["nearest"] = find_k_nearest_stations(stations, lat, lon, int(k))
    st.session_state["user_loc"] = (lat, lon)

if st.session_state["nearest"] is not None:
    lat, lon = st.session_state["user_loc"]
    nearest = st.session_state["nearest"]



    nearest = find_k_nearest_stations(stations, lat, lon, int(k))



    m = folium.Map(location=[lat, lon], zoom_start=13)
    folium.Marker([lat, lon], tooltip="Start").add_to(m)
    for _, row in nearest.iterrows():
        folium.Marker([row.start_lat, row.start_long], tooltip=row.StationName).add_to(m)

    st_folium(m, width=700, height=500)
