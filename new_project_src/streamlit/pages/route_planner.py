
import streamlit as st
import folium
from streamlit_folium import st_folium

from new_project_src.streamlit.utils import maps
from new_project_src.models.location import Location
from core.exceptions import RoutePlannerError, ErrorCode
from new_project_src.services.route_planner import RoutePlanner


def point_picker(label: str, default: tuple[float, float]) -> tuple[float, float]:
    """
    Show a folium map and let the user pick a point with a click.
    Always renders exactly ONE marker: the current selection.
    """
    # remember the current selection
    if label not in st.session_state:
        st.session_state[label] = default
    lat, lon = st.session_state[label]

    # build the map
    m = folium.Map(location=(lat, lon), zoom_start=13, control_scale=True)
    maps.add_all_stations(m)
    folium.Marker((lat, lon), icon=folium.Icon(color="green")).add_to(m)
    # show a small popup with coords on click
    folium.LatLngPopup().add_to(m)

    # render & capture the click
    rv = st_folium(m, height=300, key=f"picker_{label}")
    click = rv.get("last_clicked")

    # if the user clicked somewhere: store new coords and rerun
    if click:
        st.session_state[label] = (click["lat"], click["lng"])
        st.rerun()

    return st.session_state[label]



st.header("🚀 Plan Metro Bike Route")

with st.form("plan_route"):
    st.subheader("Start")
    s_lat, s_lon = point_picker("start_picker", (34.0522, -118.2437))

    st.subheader("Destination")
    d_lat, d_lon = point_picker("dest_picker",  (34.0635, -118.4455))

    k = st.slider("Stations to consider per side (K)", 3, 10, 5)
    plan_btn = st.form_submit_button("Plan")

# ───────────────────────── routing logic ─────────────────────────
if plan_btn:
    start = Location(latitude=s_lat, longitude=s_lon)
    dest = Location(latitude=d_lat, longitude=d_lon)

    @st.cache_resource(ttl=120)  # cache planner object – ORS client handshake is pricey
    def get_planner():
        return RoutePlanner()

    planner = get_planner()

    with st.spinner("Getting live station data & calculating best route …"):
        try:
            rp = planner.plan(start, dest, k=k)
        except RoutePlannerError as e:
            msg = {
                ErrorCode.NO_BIKE_STATION: "No nearby station with available bikes.",
                ErrorCode.NO_DOCK_STATION: "No nearby station with free docks.",
                ErrorCode.NO_CREDITS: "OpenRouteService daily credits exhausted – try again later.",
                ErrorCode.ROUTING_FAILED: "Couldn’t calculate a viable route.",
            }.get(e.code, "Unexpected error.")
            st.error(f"{msg}  \n`{e}`")
            st.stop()

    # ─────────────── summary card ────────────────
    col1, col2, col3 = st.columns(3)
    col1.metric("Total distance", f"{rp.total_distance_m/1000:.2f} km")
    col2.metric("Est. duration", f"{rp.total_duration_s/60:.0f} min")
    col3.metric("Bike share", f"{(rp.bike_route['features'][0]['properties']['summary']['distance']/rp.total_distance_m)*100:.0f}%")

    # ─────────────── map visualisation ────────────────
    fmap = maps.base_map(center=((s_lat + d_lat) / 2, (s_lon + d_lon) / 2), zoom=13)
    maps.add_all_stations(fmap)

    # helper to overlay any GeoJSON with style
    def add_geojson(geo, style, tooltip):
        folium.GeoJson(
            geo,
            style_function=lambda *_: style,
            tooltip=tooltip,
        ).add_to(fmap)

    # stations
    maps.add_station_marker(
        fmap,
        rp.origin_station.latitude,
        rp.origin_station.longitude,
        bikes=rp.origin_station.num_bikes,
        docks=rp.origin_station.num_docks,
        name=f"Origin – {rp.origin_station.name}",
    )
    maps.add_station_marker(
        fmap,
        rp.dock_station.latitude,
        rp.dock_station.longitude,
        bikes=rp.dock_station.num_bikes,
        docks=rp.dock_station.num_docks,
        name=f"Dock – {rp.dock_station.name}",
    )

    # legs
    add_geojson(
        rp.walk_to_bike,
        style={"weight": 3, "dashArray": "6,6"},
        tooltip="Walk to bike",
    )
    add_geojson(
        rp.bike_route,
        style={"weight": 4},
        tooltip="Bike segment",
    )
    add_geojson(
        rp.walk_to_dest,
        style={"weight": 3, "dashArray": "6,6"},
        tooltip="Walk to destination",
    )

    maps.show_map(fmap, key="route_map")