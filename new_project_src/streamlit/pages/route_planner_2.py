from __future__ import annotations

import json
from typing import Tuple

import folium
import streamlit as st
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh

from core.exceptions import ErrorCode, RoutePlannerError
from core.db import get_session
from new_project_src.models.location import Location
from new_project_src.models.station import Station
from new_project_src.services.route_planner import RoutePlanner
from new_project_src.streamlit.utils import maps


# ───────────────────────── helpers ──────────────────────────
def _fetch_all_stations() -> list[Station]:
    with get_session() as s:
        return (
            s.query(Station.station_id, Station.name, Station.latitude, Station.longitude)
             .order_by(Station.name)
             .all()
        )


def _mk_station_map(stations: list[Station],
                    start: Tuple[float, float] | None,
                    dest: Tuple[float, float] | None) -> folium.Map:
    # centre on LA
    fmap = maps.base_map(center=(34.05, -118.24), zoom=12)
    for stn in stations:
        pos = (stn.latitude, stn.longitude)
        colour = "blue"
        tooltip = stn.name
        # highlight current selection(s)
        if start and pos == start:
            colour, tooltip = "green", f"START: {stn.name}"
        elif dest and pos == dest:
            colour, tooltip = "red", f"DEST: {stn.name}"
        folium.CircleMarker(
            pos,
            radius=6,
            color=colour,
            fill=True,
            fill_opacity=0.9,
            tooltip=tooltip,
        ).add_to(fmap)
    return fmap


def _click_to_latlon(click_dict: dict | None) -> Tuple[float, float] | None:
    if click_dict and "lat" in click_dict and "lng" in click_dict:
        return round(click_dict["lat"], 6), round(click_dict["lng"], 6)
    return None


# ───────────────────────── UI ──────────────────────────
st.header("🚴‍♀️ Plan a Metro-Bike route")

# load stations once (takes < 100 ms)
stations_all = st.cache_data(ttl=3600)(_fetch_all_stations)()

# session-state for selections
if "start" not in st.session_state:
    st.session_state["start"] = None
if "dest" not in st.session_state:
    st.session_state["dest"] = None

col_map, col_opts = st.columns([3, 1])

with col_map:
    fmap = _mk_station_map(
        stations_all,
        st.session_state["start"],
        st.session_state["dest"],
    )
    out = st_folium(
        fmap,
        height=600,
        width="100%",
        key="stations_map",
        returned_objects=["last_object_clicked"],
    )

    # handle a click
    if out and out["last_object_clicked"]:
        latlon = _click_to_latlon(out["last_object_clicked"])
        if latlon:
            # first click -> start, second click -> dest, then toggle
            if not st.session_state["start"]:
                st.session_state["start"] = latlon
            elif not st.session_state["dest"]:
                st.session_state["dest"] = latlon
            else:
                # rotate selections
                st.session_state["start"] = st.session_state["dest"]
                st.session_state["dest"] = latlon
            st.rerun()

with col_opts:
    st.markdown("### Options")
    k = st.slider("Stations per side (k)", 2, 10, 5)
    optimise = st.checkbox("Optimise route (min duration)", value=True)
    auto_refresh = st.checkbox("Live-refresh stations (every minute)", value=False)

    if auto_refresh:
        st_autorefresh(interval=60_000, key="route_auto_refresh")

    ready = st.session_state["start"] and st.session_state["dest"]
    disabled = not ready
    plan = st.button("🚀 Plan route", disabled=disabled)

    if disabled:
        st.info("Click a **blue** station marker for start, then another for destination.")

# ───────────────────────── routing logic ──────────────────────────
if plan:
    s_lat, s_lon = st.session_state["start"]
    d_lat, d_lon = st.session_state["dest"]
    start_loc = Location(latitude=s_lat, longitude=s_lon)
    dest_loc = Location(latitude=d_lat, longitude=d_lon)

    @st.cache_resource(ttl=300)
    def _planner():
        return RoutePlanner()

    planner = _planner()

    with st.spinner("Calculating …"):
        try:
            route = planner.plan(start_loc, dest_loc, k=k if not optimise else 1)
        except RoutePlannerError as e:
            st.error({
                ErrorCode.NO_BIKE_STATION: "No bikes at the origin.",
                ErrorCode.NO_DOCK_STATION: "No docks at the destination.",
                ErrorCode.NO_CREDITS: "OpenRouteService daily credits exhausted. Try later.",
                ErrorCode.ROUTING_FAILED: "Couldn’t find a viable route.",
            }.get(e.code, f"Unexpected error: {e}"))
            st.stop()

    # ─ summary metrics ─
    st.success("### Route summary")
    m1, m2, m3 = st.columns(3)
    m1.metric("Distance", f"{route.total_distance_m/1000:.2f} km")
    m2.metric("Duration", f"{route.total_duration_s/60:.0f} min")
    share = route.bike_route["features"][0]["properties"]["summary"]["distance"]
    m3.metric("Bike share", f"{share/route.total_distance_m*100:.0f}%")

    # ─ visualise route on a fresh map ─
    route_map = maps.base_map(center=((s_lat+d_lat)/2, (s_lon+d_lon)/2), zoom=13)
    folium.Marker([s_lat, s_lon], icon=folium.Icon(color="green"), tooltip="Start").add_to(route_map)
    folium.Marker([d_lat, d_lon], icon=folium.Icon(color="red"), tooltip="Destination").add_to(route_map)

    for leg, style, tip in [
        (route.walk_to_bike, {"weight": 3, "dashArray": "6,6"}, "Walk to bike"),
        (route.bike_route,   {"weight": 4},                     "Bike"),
        (route.walk_to_dest, {"weight": 3, "dashArray": "6,6"}, "Walk to destination"),
    ]:
        folium.GeoJson(leg, style_function=lambda *_: style, tooltip=tip).add_to(route_map)

    maps.show_map(route_map, key="route_map")

    # download
    st.download_button(
        "⬇️  Full route as GeoJSON",
        json.dumps({"walk_to_bike": route.walk_to_bike,
                    "bike_route":   route.bike_route,
                    "walk_to_dest": route.walk_to_dest}),
        file_name="metro_bike_route.geojson",
        mime="application/geo+json",
    )
