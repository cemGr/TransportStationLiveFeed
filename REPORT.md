Applied Data Science with Python

Project: Transport Station Live Feed
Thomas Zehetbauer

# 1. Index

1. Task
2. Modules and Data structure
3. Tools
4. High-Level Design
5. Final Approach

# 2. Task

Process the live feed of a transportation provider and answer:
1. Given the current location and number `K`, find the `K` nearest stations that still have devices (bikes, scooters, …) available.
2. Given the current location of a person with a bike/scooter and number `K`, find the `K` nearest stations with free docks.
3. Given a source and destination (e.g. two points in Los Angeles), present a foot → bike → foot route using only station data and walking between stations.

# 3. Modules and Data structure

## 3.1 Modules
* `core/` – SQLAlchemy configuration and session helpers.
* `src/models/` – ORM models for stations, trips, live status and aggregated weather.
* `src/scraper/` – scrapers and loaders for each data source.
* `src/services/` – business logic for nearest-station queries and route planning.
* `src/streamlit/` – Streamlit application.

## 3.2 Data structure
* **Station** – physical station with geometry and relation to live status.
* **LiveStationStatus** – latest bike and dock counts for a station.
* **Trip** – historical trip record.
* **StationWeather** – hourly weather aggregated with bike usage.
* **WeatherCheckpoint** – index of the next batch of coordinates to fetch weather for.
* **RoutePlan** – result object of the route planner.
* **Location** – dataclass with latitude/longitude pairs.

# 4. Tools
* Python, SQLAlchemy, GeoAlchemy2, PostgreSQL/PostGIS for the database layer.
* Pandas, scikit‑learn for data cleaning and clustering.
* Requests, requests-cache and retry_requests for HTTP fetching.
* Openrouteservice for routing.
* Streamlit and folium for the web UI.
* Dependencies are listed in `requirements.txt`.

# 5. High-Level Design

## 5.1 Docker
The project runs all components via `docker-compose`. A PostGIS database and optional pgAdmin container are started first. Each scraper as well as the Streamlit UI are separate services based on the same Docker image. Every scraper container executes a small Python script containing a `while True:` loop that repeatedly calls `run_once()` on the respective scraper class and sleeps between runs.

```python
# pattern used by all scraper containers
if __name__ == "__main__":
    scraper = SomeScraper()
    while True:
        try:
            scraper.run_once()
        except Exception as exc:
            print("scraper error", exc, flush=True)
        time.sleep(INTERVAL)
```

## 5.2 Project
* **Database Layer** – `core/db.py` sets up the SQLAlchemy engine and provides a `get_session()` context manager.
* **Scrapers** – `StationScraper`, `TripScraper`, `LiveGeoJSONScraper` and `WeatherScraper` download external data, clean it and insert/update the database.
* **Services** – modules implementing nearest-station queries and the `RoutePlanner`.
* **Streamlit Frontend** – pages calling the services and showing results on interactive maps.

# 6. Final Approach

## 6.1 Core Assumptions
Stations form a sparse k‑NN graph. Each station is connected only to its geographically closest neighbours (k≈5–8) so the graph stays connected without too many edges.

### Task 1 – K nearest stations with bikes
1. Insert the user position as a virtual node.
2. Query a Ball‑Tree for the k nearest real stations.
3. Filter for `num_bikes_available > 0`. If too few stations remain, increase k until at least `K` valid results are found.

### Task 2 – K nearest stations with free docks
Same as Task 1 but filter on `num_docks_available > 0`.

### Task 3 – Routing source → destination
1. Use nearest‑station queries to find candidate pick‑up stations near the start and drop‑off stations near the destination.
2. For each origin/destination pair, compute three routes with OpenRouteService: start→origin (walk), origin→dock (bike) and dock→destination (walk).
3. Sum the durations, pick the combination with the shortest total time and return the full route as a `RoutePlan` object.

## 6.2 Scrapers structures
Every scraper is split into three parts:
1. **Scraper** – downloads new raw data and triggers cleaning/insertion.
2. **Cleaner** – transforms a raw file into a cleaned CSV/JSON ready for loading.
3. **Inserter** – loads the cleaned data into Postgres.

### 6.2.2 Static Station scraper
Downloads the official station table and keeps it up to date.
```python
class StationScraper:
    def run_once(self):
        url = discover_csv_url()
        raw = download(url)
        cleaned = StationCleaner(raw).clean()
        StationInserter(cleaned).upsert()
```
```python
class StationCleaner:
    def clean(self):
        df = pd.read_csv(self.raw_csv)
        df = df.drop_duplicates(subset=["Kiosk ID"])
        df.to_csv(self.out_csv, index=False)
        return self.out_csv
```
```python
class StationInserter:
    def upsert(self):
        rows = pd.read_csv(self.cleaned).to_dict("records")
        with get_session() as s:
            stmt = insert(Station).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=[Station.station_id],
                set_={c.name: c for c in stmt.excluded if c.name != "station_id"}
            )
            return s.execute(stmt).rowcount
```

### 6.2.3 Trip scraper
Fetches ZIP archives of historical trips, cleans each CSV and inserts the records.
```python
class TripScraper:
    def run_once(self):
        urls = list_trip_archives()
        for zip_url in urls:
            raw_zip = download(zip_url)
            for raw_csv in extract_csvs(raw_zip):
                cleaned = TripCleaner(raw_csv).clean()
                TripInserter(cleaned).insert()
```
```python
class TripCleaner:
    def clean(self):
        df = pd.read_csv(self.raw)
        df = canonicalise_headers(df)
        df = fill_missing_values(df)
        df.to_csv(self.out_csv, index=False)
        return self.out_csv
```
```python
class TripInserter:
    def insert(self):
        rows = pd.read_csv(self.cleaned).to_dict("records")
        with get_session() as s:
            s.bulk_insert_mappings(Trip, rows)
            return len(rows)
```

### 6.2.4 Live Station (GeoJSON) Scraper
Polls the GeoJSON live feed to update bike and dock counts.
```python
class LiveGeoJSONScraper:
    def run_once(self):
        raw = download_geojson()
        clean = LiveGeoJSONCleaner(raw).clean()
        LiveGeoJSONInserter(clean).upsert()
```
```python
class LiveGeoJSONCleaner:
    def clean(self):
        data = json.load(self.raw)
        out = {"type": "FeatureCollection", "features": data.get("features", [])}
        save(out, self.cleaned)
        return self.cleaned
```
```python
class LiveGeoJSONInserter:
    def upsert(self):
        rows = parse_features(self.clean_json)
        with get_session() as s:
            stmt = insert(LiveStationStatus).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=[LiveStationStatus.station_id],
                set_={"num_bikes": stmt.excluded.num_bikes,
                      "num_docks": stmt.excluded.num_docks,
                      "online": stmt.excluded.online,
                      "updated_at": func.now()}
            )
            return s.execute(stmt).rowcount
```

### 6.2.5 Weather “Scraper”
Aggregates hourly weather data for all trip start locations.
```python
class WeatherScraper:
    def run_once(self):
        trips = self._get_new_trips()
        coords = self._make_coord_list(trips)
        for batch in batched(coords, BATCH_SIZE):
            weather = WeatherFetcher(trips_for(batch)).fetch()
            agg = WeatherAggregator.aggregate(trips_for(batch), weather)
            WeatherInserter(agg).upsert()
```
```python
class WeatherFetcher:
    def fetch(self):
        for batch in coord_batches:
            for start, end in date_windows():
                yield fetch_weather_api(batch, start, end)
```
```python
class WeatherAggregator:
    @staticmethod
    def aggregate(trips, weather):
        join trips with hourly weather and compute statistics
        
```
```python
class WeatherInserter:
    def upsert(self):
        with get_session() as s:
            stmt = insert(StationWeather).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=[StationWeather.slot_ts, StationWeather.station_id],
                set_={c.name: c for c in stmt.excluded if c.name not in ("slot_ts", "station_id")}
            )
            return s.execute(stmt).rowcount
```

## 6.3 Services structures
Application logic is concentrated in service modules which query the database and return domain objects.

### 6.3.1 Nearest Bike and Docks Station
Provides helpers to fetch the nearest stations with available bikes or docks using PostGIS distance calculations.
```python
def nearest_stations_with_bikes(location, k):
    pt = ST_SetSRID(ST_MakePoint(location.lon, location.lat), 4326)
    query = (
        session.query(Station)
        .join(LiveStationStatus)
        .filter(LiveStationStatus.online, LiveStationStatus.num_bikes > 0)
        .order_by(ST_DistanceSphere(Station.geom, pt))
        .limit(k)
    )
    return list(query)
```
The docks function mirrors this but filters on `num_docks > 0`.

### 6.3.2 Route Planner
Combines nearest-station queries with OpenRouteService routing. It computes all station pair combinations, choosing the one with minimal total duration.
```python
class RoutePlanner:
    def plan(self, start, dest, k=3):
        origins = nearest_stations_with_bikes(start, k)
        docks = nearest_stations_with_docks(dest, k)
        origins, docks = self._adjust_for_credits(origins, docks, start, dest)
        return self._evaluate_combinations(origins, docks, start, dest)
```

## 6.4 Streamlit structures
The Streamlit app exposes simple pages to interact with the services.

### 6.4.1 Nearest Bike and Docks Station Pages
Forms collect the user location and K value, call the nearest-station services and display the result table alongside a map.
```python
with st.form("find_bikes"):
    lat, lon = widgets.lat_lon_input("Your location")
    k = st.slider("K", 1, 20, 5)
    if st.form_submit_button():
        stations = nearest_stations_with_bikes(Location(lat, lon), k)
        show_results_on_map(stations)
```

### 6.4.2 Route Planner Page
Allows users to click a start and destination on a map and then requests a route from the `RoutePlanner` service. The resulting GeoJSON is drawn over the map together with markers for the chosen stations.
```python
start = pick_point_on_map()
dest = pick_point_on_map()
if st.button("Plan route"):
    plan = RoutePlanner().plan(Location(*start), Location(*dest))
    draw_route(plan)
```
