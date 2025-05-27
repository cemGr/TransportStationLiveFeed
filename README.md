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
```bash

python src/scraper/scraper.py \
  --kind geojson \
  --dir  ./scraper_data/live \
  --interval 60
  
```

## Docker

```bash
docker build -t transport-app .
docker run --rm -p 8501:8501 transport-app
```

## Pytest

```bash
pytest -q

```

## Want to add a new Page?
```
create a python file in the src/page folder. It will be automatical added to the ui. 
```