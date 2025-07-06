from __future__ import annotations

from typing import Sequence, Mapping, Tuple
import openrouteservice as ors


def suggest_fastest_route(
    client: ors.Client,
    start: Tuple[float, float],
    dest: Tuple[float, float],
    origin_candidates: Sequence[Mapping],
    dest_candidates: Sequence[Mapping],
) -> Tuple[Mapping, Mapping, float]:
    """Return the fastest origin/destination pair and duration in minutes."""

    start_lon, start_lat = start
    dest_lon, dest_lat = dest
    matrix = getattr(client, "matrix", client.distance_matrix)

    origins = list(origin_candidates)
    dests = list(dest_candidates)
    start_coords = [[o["longitude"], o["latitude"]] for o in origins]
    end_coords = [[d["longitude"], d["latitude"]] for d in dests]

    start_walk = matrix(
        locations=[[start_lon, start_lat], *start_coords],
        profile="foot-walking",
        sources=[0],
        destinations=list(range(1, len(start_coords) + 1)),
        metrics=["duration"],
    )["durations"][0]

    end_walk_res = matrix(
        locations=[*end_coords, [dest_lon, dest_lat]],
        profile="foot-walking",
        sources=list(range(len(end_coords))),
        destinations=[len(end_coords)],
        metrics=["duration"],
    )
    end_walk = [row[0] for row in end_walk_res["durations"]]

    bike_res = matrix(
        locations=[*start_coords, *end_coords],
        profile="cycling-regular",
        sources=list(range(len(start_coords))),
        destinations=list(range(len(start_coords), len(start_coords) + len(end_coords))),
        metrics=["duration"],
    )
    bike_dur = bike_res["durations"]

    best_dur = float("inf")
    best_o = None
    best_d = None
    for i, o in enumerate(origins):
        for j, d in enumerate(dests):
            dur = (start_walk[i] + bike_dur[i][j] + end_walk[j]) / 60
            if dur < best_dur:
                best_dur = dur
                best_o = o
                best_d = d

    if best_o is None or best_d is None:
        raise RuntimeError("Unable to determine fastest route")

    return best_o, best_d, best_dur
