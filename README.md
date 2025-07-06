 In this project, I want to process the live feed of a transportation provider and
 answer the following questions:
 1. Given the current location of a person and number K as input, find K
nearest station based on available devices, e.g. bikes, scooters, etc.
 2. Given the current location of a person who has a bike/scooter and number
 Kas input, find K nearest bike/scooter stations where docks are available.
 3. Given a source and destination location, for example, Los Angeles, present
 the route on Google maps or another mapping product of a person using
Metro bike

## Project structure

```
domain/          # core entities and interfaces
usecases/        # application logic
infrastructure/  # database and external services
presentation/    # Streamlit UI (entry point in `presentation/main.py`)
src/             # supporting scripts like the scraper
tests/           # pytest suite
```

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate  # on Windows use `.venv\\Scripts\\activate`
pip install --upgrade pip
pip install -r requirements.txt
streamlit run presentation/main.py
```

```bash
#if pip install --upgrade pip is not working
python.exe -m pip install --upgrade pip
```

## 📦 Scraper

### 1 · Args **Scraper**

`src/scraper/scraper.py` downloads **raw feeds** from the LA Metro Bike-Share site  
and immediately writes a **cleaned version** to `processed_data/…`.

| CLI flag | Required | Description | Example |
|----------|----------|-------------|---------|
| `-k` / `--kind` | **yes** | What to fetch: <br>`trip` · `station` · `geojson` | `--kind trip` |
| `-d` / `--dir`  | **yes** | Folder for the **raw** files (created automatically) | `--dir ./scraper_data/trip_data` |
| `-i` / `--interval` | no (default `0`) | Repeat every *n* seconds. `0` ⇢ run once & exit. | `--interval 60` |

> **Note** – Cleaned output is always written to  
> `processed_data/static/…` and `processed_data/trip_data/…`.


### 2 · Fetch quarterly **Trip-Data** (run once a month)

```bash

python src/scraper/scraper.py \
  --kind trip \
  --dir  ./scraper_data/trip_data
  
```
```bash

python src/scraper/scraper.py \
  --kind station \
  --dir  ./scraper_data/static

```

> **Note** – Trip cleaning relies on `processed_data/static/cleaned_station_data.csv`.
> Run the station scraper once before the trip scraper, e.g. with Docker:
> ```bash
> docker compose run --rm scraper \
>   python -m src.scraper.scraper --kind station --dir ./scraper_data/static
> ```

```bash

python src/scraper/scraper.py \
  --kind geojson \
  --dir  ./scraper_data/live \
  --interval 60

```
Running the geojson scraper not only saves the snapshot but also upserts the
station data into the database.

## Docker

1. **Build the image**
   ```bash
   docker build -t transport-app .
   ```

2. **Run the UI**
   ```bash
   docker compose up ui
   ```

### Scraper via Docker

To execute the live scraper inside a container and write the data to
`./scraper_data`, use docker compose:

```bash
docker compose up scraper
docker compose run --rm trip_scraper
```

If you modify the scraper code, rebuild the container so changes are picked up:

```bash
docker compose build trip_scraper
```

The scraper will fetch the GeoJSON feed every minute and automatically
upsert the station data into the PostgreSQL database.

---

## Postgres

### 1. Start the container
```bash
docker compose up -d
```
After the database is running, the Streamlit UI will be able to connect using the
default credentials. If you see a message like `database connection failed`,
ensure this container is running and accessible on port `5432`.

### 2. Connect to the database  
```bash
docker exec -it pg_postgis psql -U radverkehr -d radstationen
```

### 3. Check table overview and structure  
- **List all tables**  
  ```sql
  \dt public.*
  ```
- **Show structure of the `stations` table**  
  ```sql
  \d public.stations
  ```

### 4. Example query: List all stations  
```sql
SELECT
  station_id,
  name,
  num_bikes,
  num_docks,
  online
FROM public.stations
ORDER BY station_id;
```

### 5. k-NN query: Find nearest stations with bikes and `online = TRUE`
```sql
WITH user_location AS (
  SELECT
    ST_SetSRID(
      ST_MakePoint(13.4000, 52.5200),
      4326
    )::GEOGRAPHY AS geom
)
SELECT
  s.station_id,
  s.name,
  s.num_bikes,
  s.num_docks,
  s.online,
  ST_Distance(s.geom, u.geom) AS distance_m
FROM public.stations AS s
CROSS JOIN user_location AS u
WHERE
  s.num_bikes > 0
  AND s.online = TRUE          -- Only stations that are online
ORDER BY
  s.geom <-> u.geom            -- k-NN search via GiST / R-Tree
LIMIT 5;
```

### Python helper
The `infrastructure/db` package provides a small helper to execute the same k-NN query
directly from Python:

```python
from infrastructure.db import query_nearest_stations

stations = query_nearest_stations(latitude=52.52, longitude=13.4, k=5)
for row in stations:
    print(row["station_id"], row["distance_m"])
```

The package also exposes a `Database` context manager for more advanced usage.

## Weather Service

The table `station_weather` stores hourly bike activity merged with the
corresponding weather observations. Each entry is unique for a combination of a
station and hour.

| Column          | Type               | Description                                    |
|-----------------|--------------------|------------------------------------------------|
| `slot_ts`       | `TIMESTAMP`        | Start of the hourly time slot (UTC)            |
| `station_id`    | `INTEGER`          | Identifier of the station                      |
| `bikes_taken`   | `INTEGER`          | Trips that started at the station within hour  |
| `bikes_returned`| `INTEGER`          | Trips that ended at the station within hour    |
| `lat`           | `DOUBLE PRECISION` | Station latitude                               |
| `lon`           | `DOUBLE PRECISION` | Station longitude                              |
| `cluster_id`    | `INTEGER`          | K‑means cluster id of the station              |
| `temperature_2m`| `REAL`             | Mean air temperature in °C                     |
| `temp_class`    | `TEXT`             | Temperature class (`cold`, `mid`, `warm`, `hot`) |
| `rain_mm`       | `REAL`             | Mean rainfall in millimetres                   |
| `is_raining`    | `BOOLEAN`          | `TRUE` if rain is at least 0.1&nbsp;mm         |
| `weather_code`  | `INTEGER`          | Most frequent weather code                     |
| `season`        | `TEXT`             | Season derived from the timestamp              |

`src/weather_service.py` processes trips in small batches to respect the
Open‑Meteo API limits. It loads up to ~60 000 new trip records on each run,
aggregates them by hour and joins the results with weather observations. The
merged rows are upserted into the `station_weather` table.

Open‑Meteo imposes rate limits which can lead to HTTP 429 errors. The service
batches up to `50` coordinates per request (`BATCH_SIZE`), caches responses and
runs every 5–15 minutes in Docker to limit the number of processed trips.

Start the service with Docker:

```bash
docker compose up weather_service
```

The service logs progress to stdout including the number of trips loaded,
weather points fetched and rows inserted. Check the container logs for details
about the most recent ingestion run.

## Pytest

```bash
pytest -q  # run from the repository root

```

### Run tests in Docker

You can also execute the test suite inside a container:

```bash
docker build -t transport-station-feed-test .
docker run --rm -v "$PWD":/app -w /app transport-station-feed-test pytest -q
```

The CI pipeline runs these commands automatically.

## Want to add a new Page?
```
Create a Python file in `presentation/pages`. It will be automatically added to the UI.
```

## OpenRouteService Notebook

`jupyter/openrouteservice_demo.ipynb` contains an example that uses
[openrouteservice](https://openrouteservice.org/) and Folium to calculate
walking and cycling routes between two coordinates and display them on a map.
The coordinates and calculated distances are stored in a Pandas DataFrame. To
run the notebook you must provide a valid API key via the environment variable
`ORS_API_KEY`, e.g.:

```bash
export ORS_API_KEY="<your-key>"
```

## Train the Random Forest model

`train_rf.py` trains a baseline Random Forest on aggregated hourly data.
Place your preprocessed dataset `trips_for_model.csv` (or the zipped
`trips_for_model.zip`) in the project root and run:

```bash
python train_rf.py
```

The script prints MAE/RMSE metrics and saves the tuned model to
`rf_hourly.pkl`.

To also predict bike returns and obtain the net bike usage you can run
`train_rf_dual.py`.  This script fits two Random Forest models – one for bikes
checked out and one for bikes returned – and stores both models as
`rf_bikes_taken.pkl` and `rf_bikes_returned.pkl`.  It uses cyclical encoding for
hour and weekday and adds per-station lag and rolling mean features to better
capture short-term usage patterns.  Net bike usage metrics are written to
`evaluation_net.txt`.
