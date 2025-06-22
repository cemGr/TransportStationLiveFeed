import streamlit as st

def lat_lon_input(label: str, default: tuple[float, float]) -> tuple[float, float]:
    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input(f"{label} latitude", value=default[0], format="%.6f")
    with col2:
        lon = st.number_input(f"{label} longitude", value=default[1], format="%.6f")
    return lat, lon
