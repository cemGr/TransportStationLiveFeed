from typing import Tuple

import streamlit as st
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

from core.db import get_session
from src.models import Station, LiveStationStatus
from src.streamlit.utils import maps
from src.models.location import Location
from core.exceptions import RoutePlannerError, ErrorCode
from src.services.route_planner import RoutePlanner

# ───────────────────────── Data helpers ─────────────────────────────
@st.cache_data(ttl=3600)
def fetch_all_stations() -> list[Station]:
    with get_session() as s:
        return (
            s.query(
                Station.station_id,
                Station.name,
                Station.latitude,
                Station.longitude,
            )
            .order_by(Station.name)
            .all()
        )

@st.cache_data(ttl=60)
def fetch_live_ids() -> set[int]:
    with get_session() as s:
        return {sid for (sid,) in s.query(LiveStationStatus.station_id).all()}

# ───────────────────────── Session state ────────────────────────────
for key in ("start", "dest"):
    st.session_state.setdefault(key, None)

def rotate_selections(new: Tuple[float, float]):
    start_selection, dest_selection = st.session_state["start"], st.session_state["dest"]

    # first click → start
    if start_selection is None:
        st.session_state["start"] = new
        return

    # second click -> dest
    if dest_selection is None:
        if new != start_selection:
            st.session_state["dest"] = new
        return

    # third click → reset
    st.session_state["start"] = None
    st.session_state["dest"] = None


# ───────────────────────── Folium utils ─────────────────────────────

def click_to_latlon(clicked: dict | None) -> Tuple[float, float] | None:
    if clicked and {"lat", "lng"} <= clicked.keys():
        return round(clicked["lat"], 6), round(clicked["lng"], 6)
    return None


def build_station_map(
    stations: list[Station],
    live_ids: set[int],
    start,
    destination,
) -> folium.Map:
    """Map with clustered stations.

    Colours:
    • blue   → station has live data
    • yellow → no live data
    • green/red override for selected start/destination
    """
    fmap = maps.base_map(center=(34.05, -118.24), zoom=12)
    cluster = MarkerCluster(name="Stations").add_to(fmap)
    pos_set = {(s.latitude, s.longitude) for s in stations}

    for station in stations:
        position = (station.latitude, station.longitude)
        colour = "blue" if station.station_id in live_ids else "yellow"
        tooltip = station.name + (" (no live data)" if colour == "yellow" else "")
        if position == start:
            colour, tooltip = "green", f"START: {station.name}"
        elif position == destination:
            colour, tooltip = "red", f"DEST: {station.name}"
        folium.CircleMarker(
            position,
            radius=6,
            color=colour,
            fill=True,
            fill_opacity=0.9,
            tooltip=tooltip,
        ).add_to(cluster)

    for pt, col, lbl in [(start, "green", "Start"), (destination, "red", "Destination")]:
        if pt and pt not in pos_set:
            folium.Marker(pt, icon=folium.Icon(color=col), tooltip=lbl).add_to(fmap)

    folium.LatLngPopup().add_to(fmap)
    return fmap

# ───────────────────────── Layout ───────────────────────────────────
st.header(" Plan a Metro‑Bike route")

stations = fetch_all_stations()
live_ids = fetch_live_ids()

col_map, col_opts = st.columns([3, 1], gap="medium")

with col_map:
    fmap = build_station_map(
        stations,
        live_ids,
        st.session_state["start"],
        st.session_state["dest"],
    )
    out = st_folium(
        fmap,
        width=1200,
        height=600,
        key="stations_map",
        returned_objects=["last_object_clicked", "last_clicked"],
    )
    latlon = (
        click_to_latlon(out.get("last_object_clicked") or out.get("last_clicked"))
        if out
        else None
    )
    if latlon:
        rotate_selections(latlon)
        st.rerun()

with col_opts:
    st.subheader("Options")
    k = st.slider("Stations per side (k)", 1, 5, 3)
    stations_with_missing_live_data = st.checkbox(
        "Include stations without live data", value=False
    )

    ready = st.session_state["start"] and st.session_state["dest"]
    plan_btn = st.button("🚀 Plan route", disabled=not ready)
    if not ready:
        st.info(
            "Click two points (or station markers) on the map to set *Start* and *Destination*. (third click to reset.)"
        )

# ───────────────────────── Routing logic ────────────────────────────
if plan_btn:
    s_lat, s_lon = st.session_state["start"]
    d_lat, d_lon = st.session_state["dest"]

    @st.cache_resource(ttl=300)
    def planner():
        return RoutePlanner()

    with st.spinner("Calculating …"):
        try:
            route_plan = planner().plan(
                Location(s_lat, s_lon),
                Location(d_lat, d_lon),
                k=k,
                stations_with_missing_live_data=stations_with_missing_live_data,
            )
        except RoutePlannerError as e:
            st.error(
                {
                    ErrorCode.NO_BIKE_STATION: "No bikes at the origin.",
                    ErrorCode.NO_DOCK_STATION: "No docks at the destination.",
                    ErrorCode.NO_CREDITS: "OpenRouteService daily credits exhausted. Try later.",
                    ErrorCode.ROUTING_FAILED: "Couldn’t find a viable route.",
                }.get(e.code, f"Unexpected error: {e}")
            )
            st.stop()

    # summary metrics
    st.success("### Route summary")
    col_distance, col_duration, col_bike_share = st.columns(3)

    col_distance.metric("Distance", f"{route_plan.total_distance_m / 1000:.2f} km")
    col_duration.metric("Duration", f"{route_plan.total_duration_s / 60:.0f} min")

    try:
        bike_dist = route_plan.bike_route["features"][0]["properties"]["summary"]["distance"]
    except (KeyError, IndexError, TypeError):
        bike_dist = getattr(route_plan, "bike_distance_m", 0) or 0
    share = bike_dist / route_plan.total_distance_m * 100 if route_plan.total_distance_m else 0
    col_bike_share.metric("Bike share", f"{share:.0f}%")

    # route map
    rmap = maps.base_map(((s_lat + d_lat) / 2, (s_lon + d_lon) / 2), zoom=13)
    for station in stations:
        position = (station.latitude, station.longitude)
        colour = "blue" if station.station_id in live_ids else "yellow"
        folium.CircleMarker(
            position,
            radius=6,
            color=colour,
            fill=True,
            fill_opacity=0.9,
            tooltip=station.name,
        ).add_to(rmap)

    for position, station, label in [
        (
                (route_plan.origin_station.latitude, route_plan.origin_station.longitude),
                route_plan.origin_station,
            "Pick‑up station",
        ),
        (
                (route_plan.dock_station.latitude, route_plan.dock_station.longitude),
                route_plan.dock_station,
            "Drop‑off station",
        ),
    ]:
        border_colour = "blue" if station.station_id in live_ids else "yellow"
        folium.CircleMarker(
            position,
            radius=8,
            color=border_colour,
            fill=True,
            fill_color="green",
            fill_opacity=1,
            tooltip=label,
        ).add_to(rmap)

    for geo, style_kwargs, tip in [
        (route_plan.walk_to_bike, {"weight": 3, "dashArray": "6,6", "color": "gray"}, "Walk to bike"),
        (route_plan.bike_route, {"weight": 4, "dashArray": None, "color": "blue"}, "Bike"),
        (
                route_plan.walk_to_dest,
                {"weight": 3, "dashArray": "6,6", "color": "gray"},
            "Walk to destination",
        ),
    ]:
        if geo:
            folium.GeoJson(
                geo,
                style_function=lambda _, kwargs=style_kwargs: kwargs,
                tooltip=tip,
            ).add_to(rmap)

    maps.show_map(rmap, key="route_map_result")
