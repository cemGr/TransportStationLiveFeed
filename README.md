# Transport Station Live Feed

This project downloads and displays live data from the LA Metro Bike Share program. The application is built with multiple components for data acquisition, processing and a Streamlit UI.

## 1. Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and `docker-compose`
- Alternatively Python 3.11+ with `pip`

## 2. Quick start

### Using Docker

1. Build the images and install dependencies

   ```bash
   docker compose build
   ```

2. Start the database

   ```bash
   docker compose up -d db
   ```

3. Load station and trip data

   ```bash
   docker compose run --rm scraper \
     python -m src.scraper.scraper --kind station --dir ./scraper_data/static
   docker compose run --rm trip_scraper
   ```

4. Optionally start the weather service in the background

   ```bash
   docker compose up -d weather_service
   ```

5. Run the Streamlit app

   ```bash
   docker build -t transport-app .
   docker run --rm -p 8501:8501 transport-app
   ```

### Local Python environment

1. Create a virtual environment

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Start Postgres following `docker-compose.yml` and then run

   ```bash
   streamlit run src/main.py
   ```

## 3. Scraper

`src/scraper/scraper.py` loads the raw data and writes cleaned files to `scraper_data/processed_data`.

| Flag         | Description                                |
|--------------|--------------------------------------------|
| `--kind`     | `trip`, `station` or `geojson`             |
| `--dir`      | Destination directory for the raw files    |
| `--interval` | Repeat interval in seconds                 |

Examples:

```bash
python -m src.scraper.scraper --kind trip --dir scraper_data/trip_data
python -m src.scraper.scraper --kind station --dir scraper_data/static
python -m src.scraper.scraper --kind geojson --dir scraper_data/live --interval 60
```

The geojson scraper updates station data in Postgres automatically.

## 4. Weather service

`src/weather_service.py` links rides with weather data and stores the results in the `station_weather` table. Start it via Docker:

```bash
docker compose up weather_service
```

Local CSV files can be read using `--trips-csv` or `--trips-dir`.

## 5. Tests

```bash
pytest -q
```

or inside a container:

```bash
docker build -t transport-station-feed-test .
docker run --rm -v "$PWD":/app -w /app transport-station-feed-test pytest -q
```

## 6. Extend the UI

Add a page by creating a Python file in `src/pages`. Streamlit picks it up automatically.

## 7. Notebooks

Example notebooks live under `jupyter/`. The OpenRouteService demo requires an API key:

```bash
export ORS_API_KEY="<your-key>"
```

