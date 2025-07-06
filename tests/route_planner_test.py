from unittest.mock import MagicMock

from usecases.route_planner import suggest_fastest_route


def test_suggest_fastest_route_selects_min_pair():
    # Mock ORS matrix responses
    matrices = [
        {"durations": [[10, 20]]},                    # start walk durations
        {"durations": [[30], [40]]},                  # end walk durations
        {"durations": [[100, 200], [300, 400]]},      # bike durations
    ]
    client = MagicMock()
    client.matrix = MagicMock(side_effect=matrices)

    origins = [
        {"name": "A", "latitude": 0.0, "longitude": 0.0},
        {"name": "B", "latitude": 0.0, "longitude": 0.0},
    ]
    dests = [
        {"name": "X", "latitude": 1.0, "longitude": 1.0},
        {"name": "Y", "latitude": 1.0, "longitude": 1.0},
    ]

    best_o, best_d, dur = suggest_fastest_route(
        client,
        (0.0, 0.0),
        (1.0, 1.0),
        origins,
        dests,
    )

    assert best_o["name"] == "A"
    assert best_d["name"] == "X"
    assert abs(dur - (10 + 100 + 30) / 60) < 1e-6
