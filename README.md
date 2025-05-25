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