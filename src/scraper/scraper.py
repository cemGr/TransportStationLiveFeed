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
from datetime import datetime, timezone
from enum import Enum
from tqdm import tqdm
from pathlib import Path

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

def stream_download(url: str, dest: Path, session: requests.Session):
    if dest.exists():
        return False         # already present
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
    return True

# ------------------------------------------------------------------ SCRAPER IMPLEMENTATIONS
def scrape_trip(dest_dir: Path, session: requests.Session):
    html   = session.get(DATA_PAGE, timeout=TIMEOUT).text
    soup   = BeautifulSoup(html, "html.parser")
    links  = {urljoin(DATA_PAGE, a["href"]) for a in soup.select("a[href]")
              if ZIP_RE.search(a["href"])}
    fresh = 0
    for url in sorted(links, reverse=True):
        target = dest_dir / os.path.basename(url)
        fresh += stream_download(url, target, session)
    print(f"Trip-data: {fresh} new file(s)")

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
    json.loads(r.text)
    write_atomic(target, r.content)
    print("GeoJSON snapshot:", target.name)

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
