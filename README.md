# LA Metro Bike Share Tools

This project ingests public data from the **Metro Bike Share** program in Los Angeles and provides tools to explore that data.  It collects station locations, live bike availability, trip information and matching weather data.  A Streamlit web interface lets you find nearby bikes or docks and plan a route that combines walking and cycling.

## Features

- **Station scraper** – downloads the official station table, cleans it and upserts it into a PostGIS database.
- **Trip scraper** – fetches zip archives of historical trips and loads them into the database.
- **Live feed scraper** – periodically retrieves the GeoJSON feed of station status.
- **Weather ingestion** – joins trip records with hourly weather from Open‑Meteo.
- **Route planner** – uses OpenRouteService to compute a walk → bike → walk route between two points.
- **Streamlit UI** – interactive pages to find bikes/docks and visualise planned routes on a map.

### Installing Requirements

Install the dependencies:

```bash

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

```

## Development setup

The easiest way to run everything is via [Docker Compose](docker-compose.yml).  It spins up a PostGIS database, optional pgAdmin and all scraper services.

```bash
# build images and start the stack
$ docker-compose up --build
```

The Streamlit app will be available at `http://localhost:8003` once the services have started.

### Environment variables

Copy `.env` and adjust as needed:

- `ORS_API_KEY` – your OpenRouteService API key (required for the route planner).
- `DATABASE_URL` – connection string used by the application and scrapers.

## License

This project is provided under the MIT License.