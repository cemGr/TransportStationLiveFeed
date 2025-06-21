# new_project_src/scraper/live_geojson/scraper.py

from __future__ import annotations
from pathlib import Path
import requests

from new_project_src.bikemetro.constants import DATA_PAGE, HEADERS, TIMEOUT
from new_project_src.bikemetro.helpers import get_soup, first_href, stream_download

from new_project_src.scraper.live_geojson.cleaner  import LiveGeoJSONCleaner
from new_project_src.scraper.live_geojson.inserter import LiveGeoJSONInserter

class LiveGeoJSONScraper:
    """
    Fetch the live station-status GeoJSON by first scraping the Metro data page
    for the current GeoJSON link, then cleaning & inserting.
    """

    RAW_DIR   = Path("/app/data/raw/live")
    CLEAN_DIR = Path("/app/data/processed/live")

    def __init__(self):
        self.RAW_DIR.mkdir(parents=True, exist_ok=True)
        self.CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    def run_once(self) -> None:
        # 1) hit the data page and find the GeoJSON link
        with requests.Session() as sess:
            sess.headers.update(HEADERS)
            soup    = get_soup(sess)
            geo_url = first_href(soup, "GeoJSON")
            if not geo_url:
                print("⚠ GeoJSON link not found on data page")
                return

            # 2) download the snapshot
            raw_path = self.RAW_DIR / Path(geo_url).name
            stream_download(geo_url, raw_path, sess)

        # 3) clean & insert
        cleaner  = LiveGeoJSONCleaner(raw_path, self.CLEAN_DIR)
        cleaned  = cleaner.clean()
        inserter = LiveGeoJSONInserter(cleaned)
        inserter.upsert()
