 In this project, I want to process the live feed of a transportation provider and
 answer the following questions:
 1. Given the current location of a person and number K as input, find K
nearest station based on available devices, e.g. bikes, scooters, etc.
 2. Given the current location of a person who has a bike/scooter and number
 Kas input, find K nearest bike/scooter stations where docks are available.
 3. Given a source and destination location, for example, Los Angeles, present
 the route on Google maps or another mapping product of a person using
 Metro bike

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip 
pip install -r requirements.txt
streamlit run src/main.py
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

2. **Run the container**
   ```bash
   docker run --rm -p 8501:8501 transport-app
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
After the database is running, the Streamlit UI will be able to connect via the
default credentials. If you see a message like `Datenbankverbindung
fehlgeschlagen`, ensure this container is running and accessible on port `5432`.

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
The `src/db` package provides a small helper to execute the same k-NN query
directly from Python:

```python
from src.db import query_nearest_stations

stations = query_nearest_stations(latitude=52.52, longitude=13.4, k=5)
for row in stations:
    print(row["station_id"], row["distance_m"])
```

The package also exposes a `Database` context manager for more advanced usage.

## Pytest

```bash
pytest -q

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
create a python file in the src/page folder. It will be automatical added to the ui.
```

## OpenRouteService Notebook

In `jupyter/openrouteservice_demo.ipynb` findest du ein Beispiel, das mithilfe
von [openrouteservice](https://openrouteservice.org/) und Folium die Distanz
und Route zwischen zwei Koordinaten sowohl zu Fuß als auch mit dem Fahrrad
berechnet und auf einer Karte anzeigt. Die Koordinaten und die ermittelten
Distanzen werden in einem Pandas-DataFrame gespeichert. Um das Notebook
auszuführen, musst du einen gültigen API-Key über die Umgebungsvariable
`ORS_API_KEY` bereitstellen, z.B.:

```bash
export ORS_API_KEY="<dein-key>"
```
