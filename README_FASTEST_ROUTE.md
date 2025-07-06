# Route Planner – Suggest Fastest Option

This document summarizes how the **Suggest fastest option** button on the Route Planner page computes the optimal bike‑share route.

## Problems Addressed

1. **Find K nearest stations with bikes**
2. **Find K nearest stations with free docks**
3. **Suggest fastest route using walking and cycling**

## High Level Flow

```text
[User start]
    |
    |--(1) search stations with bikes  --> list of origins
    |--(2) search stations with docks  --> list of destinations
    |
    '--(3) evaluate all origin/destination pairs
                 |
                 '--choose pair with minimum total duration
```

## Pseudocode Summary

### 1. Nearest stations with bikes
```pseudo
function find_nearest_stations(repo, lat, lon, k):
    return repo.nearest_stations(lat, lon, k)
```
*Returns a list of station mappings ordered by distance.*

### 2. Nearest stations with docks
```pseudo
function find_nearest_docks(repo, lat, lon, k):
    return repo.nearest_docks(lat, lon, k)
```
*Same as above but filtered by available docks.*

### 3. Suggest fastest route
```pseudo
function suggest_fastest_route(client, start, dest, origins, dests):
    walk_start = matrix(client, start -> origins, mode="walk")
    bike = matrix(client, origins -> dests, mode="bike")
    walk_end = matrix(client, dests -> dest, mode="walk")
    for each origin i in origins:
        for each dest j in dests:
            total = walk_start[i] + bike[i][j] + walk_end[j]
            keep minimum
    return best_origin, best_dest, best_total_minutes
```

## Key Functions & Parameters

- **find_nearest_stations(repo, latitude, longitude, k=5)**
  - *repo*: database repository
  - *latitude*, *longitude*: user coordinates
  - *k*: number of stations
  - *Output*: list of dicts containing `name`, `num_bikes`, `distance_m`, etc.

- **find_nearest_docks(repo, latitude, longitude, k=5)**
  - Same parameters as above
  - *Output*: list of dicts with `num_docks` information

- **suggest_fastest_route(client, start, dest, origin_candidates, dest_candidates)**
  - *client*: `openrouteservice.Client`
  - *start*: `(lon, lat)` tuple for user start
  - *dest*: `(lon, lat)` tuple for user destination
  - *origin_candidates*: results from `find_nearest_stations`
  - *dest_candidates*: results from `find_nearest_docks`
  - *Returns*: `(origin_dict, dest_dict, duration_minutes)` representing the fastest option

Sample output for `suggest_fastest_route`:
```python
(
    {'station_id': 15, 'name': 'Main St', 'latitude': 34.05, 'longitude': -118.23},
    {'station_id': 8, 'name': 'Broadway', 'latitude': 34.06, 'longitude': -118.24},
    12.7  # minutes
)
```
