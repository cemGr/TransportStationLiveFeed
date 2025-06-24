import os
import streamlit as st
import folium
from dotenv import load_dotenv
from streamlit_folium import st_folium
import openrouteservice as ors

from infrastructure.db import DBStationRepository
from usecases.stations import find_nearest_stations, find_nearest_docks


@st.cache_data(show_spinner=False)
def _get_ors_client(api_key: str) -> ors.Client:
    """Return a memoised ORS client instance."""
    return ors.Client(key=api_key)


def _make_route(
    client: ors.Client, coords: list[list[float]], profile: str
) -> list[list[float]]:
    """Call ORS directions and return decoded lat/lon pairs."""
    data = client.directions(coords, profile=profile, format="geojson")
    geometry = data["features"][0]["geometry"]["coordinates"]  # lon/lat pairs
    return [[lat, lon] for lon, lat in geometry]


def _add_route(map_: folium.Map, points: list[list[float]], tooltip: str, color: str):
    folium.PolyLine(points, tooltip=tooltip, color=color).add_to(map_)


def _get_api_key() -> str:
    load_dotenv()
    return os.getenv("ORS_API_KEY", "")


st.set_page_config(
    page_title="\U0001f6b4 Route Planner", page_icon="\U0001f6b4", layout="wide"
)
st.title("\U0001f6b4 Bike‑Share Route Planner")

api_key = _get_api_key()
if not api_key:
    st.warning(
        "Please store an OpenRouteService API key first (\u2699\ufe0f Settings or environment variable `ORS_API_KEY`)."
    )
    st.stop()

with st.form("route_form"):
    st.markdown("### Start coordinates (your location)")
    c1, c2 = st.columns(2)
    start_lat = c1.number_input("Latitude", value=34.05, format="%.5f")
    start_lon = c2.number_input("Longitude", value=-118.25, format="%.5f")

    st.markdown("### Destination coordinates")
    c3, c4 = st.columns(2)
    dest_lat = c3.number_input("Latitude ", value=34.06, format="%.5f")
    dest_lon = c4.number_input("Longitude ", value=-118.24, format="%.5f")

    k = st.number_input("Number of nearby stations", min_value=1, value=5, step=1)
    submitted = st.form_submit_button("Find stations")

if "step" not in st.session_state:
    st.session_state["step"] = 0

if submitted:
    try:
        with DBStationRepository() as repo:
            origin_opts = find_nearest_stations(
                repo, latitude=start_lat, longitude=start_lon, k=int(k)
            )
            dest_opts = find_nearest_docks(
                repo, latitude=dest_lat, longitude=dest_lon, k=int(k)
            )
    except Exception as exc:
        st.error(f"Error while querying stations: {exc}")
        st.stop()

    if not origin_opts:
        st.error("No stations with bikes near the start were found.")
        st.stop()
    if not dest_opts:
        st.error("No stations with free docks near the destination were found.")
        st.stop()

    st.session_state["origin_candidates"] = origin_opts
    st.session_state["dest_candidates"] = dest_opts
    st.session_state["step"] = 1

if st.session_state.get("step") == 1:
    st.subheader("1️⃣ Select stations")

    origin_sel = {
        f"{row['name']} (≈{row['distance_m']:.0f} m | {row.get('num_bikes', '–')}  Bikes)": row
        for row in st.session_state["origin_candidates"]
    }
    dest_sel = {
        f"{row['name']} (≈{row['distance_m']:.0f} m | {row.get('num_docks', '–')}  Docks)": row
        for row in st.session_state["dest_candidates"]
    }

    sc1, sc2 = st.columns(2)
    origin_choice = sc1.selectbox("Start station", list(origin_sel.keys()))
    dest_choice = sc2.selectbox("Destination station", list(dest_sel.keys()))

    if st.button("Calculate route 🚀"):
        st.session_state["origin_station"] = origin_sel[origin_choice]
        st.session_state["dest_station"] = dest_sel[dest_choice]
        st.session_state["step"] = 2

if st.session_state.get("step") == 2:
    st.subheader("2️⃣ Optimal route")

    client = _get_ors_client(api_key)

    user_start = [start_lat, start_lon]
    user_dest = [dest_lat, dest_lon]
    s_station = [
        st.session_state["origin_station"]["latitude"],
        st.session_state["origin_station"]["longitude"],
    ]
    d_station = [
        st.session_state["dest_station"]["latitude"],
        st.session_state["dest_station"]["longitude"],
    ]

    try:
        walk1 = _make_route(
            client,
            [[user_start[1], user_start[0]], [s_station[1], s_station[0]]],
            profile="foot-walking",
        )
        bike = _make_route(
            client,
            [[s_station[1], s_station[0]], [d_station[1], d_station[0]]],
            profile="cycling-regular",
        )
        walk2 = _make_route(
            client,
            [[d_station[1], d_station[0]], [user_dest[1], user_dest[0]]],
            profile="foot-walking",
        )
    except Exception as exc:
        st.error(f"OpenRouteService request failed: {exc}")
        st.stop()

    m_center = [(user_start[0] + user_dest[0]) / 2, (user_start[1] + user_dest[1]) / 2]
    m = folium.Map(location=m_center, zoom_start=13)

    folium.Marker(user_start, tooltip="Start", icon=folium.Icon(color="red")).add_to(m)
    folium.Marker(
        user_dest, tooltip="Destination", icon=folium.Icon(color="darkred")
    ).add_to(m)
    folium.Marker(
        s_station,
        tooltip=f"Start station: {st.session_state['origin_station']['name']}",
        icon=folium.Icon(color="blue"),
    ).add_to(m)
    folium.Marker(
        d_station,
        tooltip=f"Destination station: {st.session_state['dest_station']['name']}",
        icon=folium.Icon(color="green"),
    ).add_to(m)

    _add_route(m, walk1, tooltip="Walk ➀", color="orange")
    _add_route(m, bike, tooltip="Bike segment", color="blue")
    _add_route(m, walk2, tooltip="Walk ➁", color="orange")

    st_folium(m, width=900, height=600)

    with st.expander("Details"):
        st.markdown(
            f"* **Start station:** {st.session_state['origin_station']['name']} «{st.session_state['origin_station']['distance_m']:.0f} m»\n"
            f"* **Destination station:** {st.session_state['dest_station']['name']} «{st.session_state['dest_station']['distance_m']:.0f} m»"
        )
