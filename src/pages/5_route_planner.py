import os
import sys
from pathlib import Path

import streamlit as st
import folium
from dotenv import load_dotenv
from streamlit_folium import st_folium
import openrouteservice as ors

# Ensure repository root is on the Python path so that ``src`` resolves
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

# ────────────────────────────────────────────────────────────────────────────────
# Local imports (database helpers + offline fallback)
# ────────────────────────────────────────────────────────────────────────────────
try:
    # When the DB container is available
    from src.db import query_nearest_stations, query_nearest_docks
except Exception:
    print("failed to import DB helpers")
    # # Development/off‑line mode – use STR‑tree lookup
    # from src.datastructure.rtree import find_k_nearest_stations as _offline_knn
    #
    # @st.cache_data
    # def _load_station_snapshot() -> pd.DataFrame:
    #     """Load cleaned station snapshot shipped with the repo (offline mode)."""
    #     data_path = REPO_ROOT / "jupyter" / "cleaned_station_data.csv"
    #     df = pd.read_csv(data_path)
    #     df = df.rename(
    #         columns={
    #             "Kiosk Name": "name",
    #             "Latitude": "latitude",
    #             "Longitude": "longitude",
    #             "Status": "status",
    #         }
    #     )
    #     return df[df["status"] == "Active"].reset_index(drop=True)
    #
    # _STATIONS_FALLBACK = _load_station_snapshot()
    #
    # def query_nearest_stations(latitude: float, longitude: float, k: int = 5):
    #     df = _offline_knn(_STATIONS_FALLBACK, latitude, longitude, k)
    #     return [
    #         {
    #             "station_id": None,
    #             "name": row.StationName,
    #             "longitude": row.start_long,
    #             "latitude": row.start_lat,
    #             "distance_m": row.distance,
    #             "num_bikes": None,
    #         }
    #         for row in df.itertuples(index=False)
    #     ]
    #
    # # For docks we just re‑use the same distance‑only fallback
    # query_nearest_docks = query_nearest_stations  # type: ignore

# ────────────────────────────────────────────────────────────────────────────────
# Helper functions
# ────────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _get_ors_client(api_key: str) -> ors.Client:
    """Return a memoised ORS client instance."""
    return ors.Client(key=api_key)


def _make_route(client: ors.Client, coords: list[list[float]], profile: str) -> list[list[float]]:
    """Call ORS directions and return decoded lat/lon pairs."""
    data = client.directions(coords, profile=profile, format="geojson")
    geometry = data["features"][0]["geometry"]["coordinates"]  # lon/lat pairs
    return [[lat, lon] for lon, lat in geometry]


def _add_route(map_: folium.Map, points: list[list[float]], tooltip: str, color: str):
    folium.PolyLine(points, tooltip=tooltip, color=color).add_to(map_)


def _get_api_key() -> str:
    load_dotenv()
    return os.getenv("ORS_API_KEY", "")


# ────────────────────────────────────────────────────────────────────────────────
# Streamlit UI
# ────────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="🚴‍♂️ Route Planner", page_icon="🚴‍♂️", layout="wide")
st.title("🚴‍♂️ Bike‑Share Route Planner")

api_key = _get_api_key()
if not api_key:
    st.warning("Bitte erst einen OpenRouteService‑API‑Key speichern (⚙️ Einstellungen oder Environment‐Variable `ORS_API_KEY`).")
    st.stop()

# ─────────── input form ───────────
with st.form("route_form"):
    st.markdown("### Startkoordinaten (Ihr Standort)")
    c1, c2 = st.columns(2)
    start_lat = c1.number_input("Latitude", value=34.05, format="%.5f")
    start_lon = c2.number_input("Longitude", value=-118.25, format="%.5f")

    st.markdown("### Zielkoordinaten")
    c3, c4 = st.columns(2)
    dest_lat = c3.number_input("Latitude ", value=34.06, format="%.5f")
    dest_lon = c4.number_input("Longitude ", value=-118.24, format="%.5f")

    k = st.number_input("Anzahl nächster Stationen", min_value=1, value=5, step=1)
    submitted = st.form_submit_button("Stationen suchen")

# state machine: 0‑nothing, 1‑choose stations, 2‑show route
if "step" not in st.session_state:
    st.session_state["step"] = 0

if submitted:
    try:
        origin_opts = query_nearest_stations(latitude=start_lat, longitude=start_lon, k=int(k))
        dest_opts = query_nearest_docks(latitude=dest_lat, longitude=dest_lon, k=int(k))
    except Exception as exc:
        st.error(f"Fehler bei der Stationsabfrage: {exc}")
        st.stop()

    if not origin_opts:
        st.error("Keine Stationen mit Bikes in der Nähe des Starts gefunden.")
        st.stop()
    if not dest_opts:
        st.error("Keine Stationen mit freien Docks am Ziel gefunden.")
        st.stop()

    st.session_state["origin_candidates"] = origin_opts
    st.session_state["dest_candidates"] = dest_opts
    st.session_state["step"] = 1

# ─────────── station selection ───────────
if st.session_state.get("step") == 1:
    st.subheader("1️⃣ Stationen auswählen")

    origin_sel = {
        f"{row['name']} (≈{row['distance_m']:.0f} m | {row.get('num_bikes', '–')} Bikes)": row
        for row in st.session_state["origin_candidates"]
    }
    dest_sel = {
        f"{row['name']} (≈{row['distance_m']:.0f} m | {row.get('num_docks', '–')} Docks)": row
        for row in st.session_state["dest_candidates"]
    }

    sc1, sc2 = st.columns(2)
    origin_choice = sc1.selectbox("Start‑Station", list(origin_sel.keys()))
    dest_choice = sc2.selectbox("Ziel‑Station", list(dest_sel.keys()))

    if st.button("Route berechnen 🚀"):
        st.session_state["origin_station"] = origin_sel[origin_choice]
        st.session_state["dest_station"] = dest_sel[dest_choice]
        st.session_state["step"] = 2

# ─────────── build & display map ───────────
if st.session_state.get("step") == 2:
    st.subheader("2️⃣ Optimale Route")

    client = _get_ors_client(api_key)

    # collect coordinates (lat, lon)
    user_start = [start_lat, start_lon]
    user_dest = [dest_lat, dest_lon]
    s_station = [st.session_state["origin_station"]["latitude"], st.session_state["origin_station"]["longitude"]]
    d_station = [st.session_state["dest_station"]["latitude"], st.session_state["dest_station"]["longitude"]]

    try:
        walk1 = _make_route(client, [[user_start[1], user_start[0]], [s_station[1], s_station[0]]], profile="foot-walking")
        bike = _make_route(client, [[s_station[1], s_station[0]], [d_station[1], d_station[0]]], profile="cycling-regular")
        walk2 = _make_route(client, [[d_station[1], d_station[0]], [user_dest[1], user_dest[0]]], profile="foot-walking")
    except Exception as exc:
        st.error(f"OpenRouteService‑Anfrage fehlgeschlagen: {exc}")
        st.stop()

    m_center = [(user_start[0] + user_dest[0]) / 2, (user_start[1] + user_dest[1]) / 2]
    m = folium.Map(location=m_center, zoom_start=13)

    # markers
    folium.Marker(user_start, tooltip="Start", icon=folium.Icon(color="red")).add_to(m)
    folium.Marker(user_dest, tooltip="Ziel", icon=folium.Icon(color="darkred")).add_to(m)
    folium.Marker(s_station, tooltip=f"Start‑Station: {st.session_state['origin_station']['name']}", icon=folium.Icon(color="blue")).add_to(m)
    folium.Marker(d_station, tooltip=f"Ziel‑Station: {st.session_state['dest_station']['name']}", icon=folium.Icon(color="green")).add_to(m)

    # routes
    _add_route(m, walk1, tooltip="Fußweg ➀", color="orange")
    _add_route(m, bike, tooltip="Radstrecke", color="blue")
    _add_route(m, walk2, tooltip="Fußweg ➁", color="orange")

    st_folium(m, width=900, height=600)

    with st.expander("Details"):
        st.markdown(
            f"* **Start‑Station:** {st.session_state['origin_station']['name']} «{st.session_state['origin_station']['distance_m']:.0f} m»\n"
            f"* **Ziel‑Station:** {st.session_state['dest_station']['name']} «{st.session_state['dest_station']['distance_m']:.0f} m»"
        )
