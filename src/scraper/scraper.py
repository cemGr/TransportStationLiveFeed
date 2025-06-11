"""
scraper.py  –  Download data files for LA Metro Bike Share.

USAGE examples
--------------
# Trip data, once a month (cron)
python src/scraper/scraper.py --kind trip --dir ./scraper_data/trip_data --interval 2628000

# Station table, run manually (script decides if it has changed)
python src/scraper/scraper.py --kind station --dir ./scraper_data/static

# GeoJSON (live status), every minute in a while-loop
python src/scraper/scraper.py --kind geojson --dir ./scraper_data/live --interval 60
"""
from __future__ import annotations
import argparse, time, os, re, sys, json, requests
import shutil
import zipfile
from datetime import datetime, timezone
from enum import Enum
from tqdm import tqdm
from pathlib import Path

# Ensure project root is on sys.path when executed directly
if __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.data_processor.data_processor import clean_trip_csv, clean_station_csv
from src.db.connection import open_connection
from src.db.loaders import upsert_stations_from_json, insert_trips_from_csv


# ------------------------------------------------------------------ ENUM & CONFIG
class Kind(Enum):
    trip     = "trip"
    station  = "station"
    geojson  = "geojson"

DATA_PAGE       = "https://bikeshare.metro.net/about/data/"
STATION_URL    = "https://bikeshare.metro.net/static/station_table.csv"
GEOJSON_URL    = "https://bikeshare.metro.net/stations/stations.geojson"
ZIP_RE         = re.compile(r"\btrips?.*\.zip$", re.I)
UA             = "MetroScraper/1.0"
TIMEOUT        = 30

HEADERS_BROWSER = {
    "User-Agent": UA,
    "Accept-Language": "en-US,en;q=0.9",
}

from bs4 import BeautifulSoup
from urllib.parse import urljoin

def _get_data_page(session: requests.Session) -> BeautifulSoup:
    html = session.get(DATA_PAGE, headers=HEADERS_BROWSER, timeout=TIMEOUT).text
    return BeautifulSoup(html, "html.parser")

def _first_href(soup: BeautifulSoup, text_contains: str) -> str | None:
    """Return absolute href whose link-text contains the phrase (case-insensitive)."""
    link = soup.find("a", string=lambda t: t and text_contains.lower() in t.lower())
    return urljoin(DATA_PAGE, link["href"]) if link else None
# ------------------------------------------------------------------ HELPERS
def write_atomic(path: Path, content: bytes):
    tmp = path.with_suffix(".part")
    tmp.write_bytes(content)
    tmp.rename(path)

def stream_download(url: str, dest: Path, session: requests.Session) -> Path | None:
    if dest.exists():
        return None
    with session.get(url, stream=True, timeout=TIMEOUT) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with tqdm(total=total, unit="B", unit_scale=True,
                  desc=dest.name) as bar, \
             open(dest.with_suffix(".part"), "wb") as f:
            for chunk in r.iter_content(1 << 15):
                f.write(chunk)
                bar.update(len(chunk))
    dest.with_suffix(".part").rename(dest)
    return dest

# ------------------------------------------------------------------ SCRAPER IMPLEMENTATIONS

def scrape_trip(dest_dir: Path, session: requests.Session):
    html = session.get(DATA_PAGE, timeout=TIMEOUT).text
    soup = BeautifulSoup(html, "html.parser")
    links = {urljoin(DATA_PAGE, a["href"]) for a in soup.select("a[href]")
             if ZIP_RE.search(a["href"])}

    extracted, skipped = 0, 0
    for url in sorted(links, reverse=True):
        zip_path = stream_download(url, dest_dir / os.path.basename(url), session)
        if not zip_path:
            skipped += 1
            continue

        extract_trip_zip(dest_dir, zip_path)

        zip_path.unlink()
        extracted += 1

    print(f"Trip-data: {extracted} new archive(s) extracted, {skipped} already present")


def extract_trip_zip(dest_dir, zip_path):
    STATION_RE = re.compile(r"metro-bike-share-stations-\d{4}-\d{2}-\d{2}\.csv$", re.I)

    with zipfile.ZipFile(zip_path) as zf:
        members = zf.infolist()

        # first handle any station tables so trip cleaning succeeds
        for m in members:
            if m.is_dir():
                continue
            name = Path(m.filename).name
            if STATION_RE.match(name):
                if m.filename.startswith("__MACOSX/") or name.startswith("._"):
                    continue
                station_raw = STATIC_DIR / name
                if not station_raw.exists():
                    with zf.open(m) as src, open(station_raw, "wb") as out:
                        shutil.copyfileobj(src, out)
                try:
                    clean_station_csv(station_raw, STATIC_DIR)
                except Exception as exc:
                    print(f"Warning: failed to clean station data {name}: {exc}")

        for m in members:
            if m.is_dir():
                continue

            # Unique case only in some zips
            if m.filename.startswith("__MACOSX/") or Path(m.filename).name.startswith("._"):
                continue

            name = Path(m.filename).name
            if STATION_RE.match(name):
                # already processed above
                continue

            dst_file = dest_dir / Path(m.filename).name
            if dst_file.exists():
                continue
            with zf.open(m) as src, open(dst_file, "wb") as out:
                shutil.copyfileobj(src, out)

            # run cleaner immediately if station data is available

            station_csv = STATIC_DIR / "cleaned_station_data.csv"
            if not station_csv.exists():

                print(
                    "Warning: cleaned station data missing; "
                    "run the station scraper first"
                )
            else:
                try:
                    cleaned = clean_trip_csv(dst_file, station_csv, TRIP_DIR)
                except Exception as exc:
                    print(f"Warning: failed to clean trip data {dst_file.name}: {exc}")
                    cleaned = None

                if cleaned:
                    conn = open_connection()
                    try:
                        insert_trips_from_csv(cleaned, conn)
                    finally:
                        conn.close()


def scrape_station(dest_dir: Path, session: requests.Session):
    soup = _get_data_page(session)
    csv_url = _first_href(soup, "Station Table")
    if not csv_url:
        print("Warning: Station-table link not found")
        return

    target = dest_dir / Path(csv_url).name
    r = session.get(csv_url, timeout=TIMEOUT)
    r.raise_for_status()

    if target.exists() and target.read_bytes() == r.content:
        print("Station table unchanged – skipped")
    else:
        write_atomic(target, r.content)
        print("Station table saved:", target.name)

    #  run cleaner immediately sollte hier es in der db gespeichert werden?
    clean_station_csv(target, STATIC_DIR)

def scrape_geojson(dest_dir: Path, session: requests.Session):
    soup = _get_data_page(session)
    geo_url = _first_href(soup, "GeoJSON")
    if not geo_url:
        print("Warning: GeoJSON link not found")
        return

    ts_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = dest_dir / f"stations_{ts_utc}.json"
    r = session.get(geo_url, timeout=TIMEOUT)
    r.raise_for_status()

    data = json.loads(r.text)
    pretty = json.dumps(data, indent=2).encode()
    write_atomic(target, pretty)
    print("GeoJSON snapshot:", target.name)
    conn = open_connection()
    try:
        upsert_stations_from_json(target, conn)
    finally:
        conn.close()

# ------------------------------------------------------------------ MAIN LOOP
SCRAPER_MAP = {
    Kind.trip:     scrape_trip,
    Kind.station:  scrape_station,
    Kind.geojson:  scrape_geojson,
}

def run_once(kind: Kind, dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    with requests.Session() as sess:
        sess.headers["User-Agent"] = UA
        SCRAPER_MAP[kind](dest, sess)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-k", "--kind", required=True,
                    choices=[k.value for k in Kind],
                    help="trip | station | geojson")
    ap.add_argument("-d", "--dir", required=True,
                    help="destination directory for downloaded files")
    ap.add_argument("-i", "--interval", type=int, default=0,
                    help="seconds between runs (0 = run once and exit)")
    args = ap.parse_args()

    kind = Kind(args.kind)
    dest = Path(args.dir)

    RAW_ROOT  = dest
    PROC_ROOT = RAW_ROOT.parent / "processed_data"
    global STATIC_DIR, TRIP_DIR
    STATIC_DIR = PROC_ROOT / "static"
    TRIP_DIR = PROC_ROOT / "trip_data"
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    TRIP_DIR.mkdir(parents=True, exist_ok=True)

    if args.interval <= 0:
        run_once(kind, dest)
        return

    while True:
        try:
            run_once(kind, dest)
        except Exception as exc:
            print("⚠", exc, file=sys.stderr)
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
