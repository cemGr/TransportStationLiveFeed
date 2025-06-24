from __future__ import annotations
import sys
from pathlib import Path
from typing import Callable

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# Ensure repository root is on the Python path so imports work with Streamlit
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))


def station_search_page(
    *,
    title: str,
    state_key: str,
    search_func: Callable[[object, float, float, int], list[dict]],
    result_col: str,
    value_label: str,
    icon_color: str,
) -> None:
    """Render a simple station search page."""

    st.title(title)

    if state_key not in st.session_state:
        st.session_state[state_key] = None
        st.session_state["user_loc"] = None

    with st.form(f"{state_key}_form"):
        lat = st.number_input("Latitude", value=34.05, format="%.5f")
        lon = st.number_input("Longitude", value=-118.25, format="%.5f")
        k = st.number_input("Number of stations", min_value=1, value=5, step=1)
        submitted = st.form_submit_button("search")

    if submitted:
        try:
            from infrastructure.db import DBStationRepository

            with DBStationRepository() as repo:
                st.session_state[state_key] = search_func(
                    repo, latitude=lat, longitude=lon, k=int(k)
                )
            st.session_state["user_loc"] = (lat, lon)
        except Exception as exc:  # pragma: no cover - UI feedback
            st.error(f"Database connection failed: {exc}")

    results = st.session_state.get(state_key)
    if results:
        lat, lon = st.session_state["user_loc"]
        df = pd.DataFrame(results)
        df["distance_m"] = df["distance_m"].round(1)
        st.subheader("Available stations")
        st.table(df[["name", result_col, "distance_m"]])

        m = folium.Map(location=[lat, lon], zoom_start=13)
        folium.Marker([lat, lon], tooltip="You", icon=folium.Icon(color="red")).add_to(
            m
        )
        for row in results:
            folium.Marker(
                [row["latitude"], row["longitude"]],
                tooltip=f"{row['name']} ({row[result_col]} {value_label})",
                icon=folium.Icon(color=icon_color),
            ).add_to(m)

        st_folium(m, width=700, height=500)
