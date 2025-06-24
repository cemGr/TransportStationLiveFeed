from __future__ import annotations
from pathlib import Path
import requests

from new_project_src.bikemetro.constants import HEADERS
from new_project_src.bikemetro.helpers import get_soup, first_href, stream_download

from new_project_src.scraper.station.cleaner   import StationCleaner
from new_project_src.scraper.station.inserter  import StationInserter

class StationScraper:

    RAW_DIR   = Path("/app/data/raw/station")
    PROC_DIR  = Path("/app/data/processed/station")

    def __init__(self):
        self.RAW_DIR.mkdir(parents=True, exist_ok=True)
        self.PROC_DIR.mkdir(parents=True, exist_ok=True)

    def run_once(self) -> None:
        with requests.Session() as sess:
            sess.headers.update(HEADERS)
            soup    = get_soup(sess)
            csv_url = first_href(soup, "Station Table")
            if not csv_url:
                print("⚠ Station-table link not found")
                return

            raw_path = self.RAW_DIR / Path(csv_url).name
            if not raw_path.exists():
                stream_download(csv_url, raw_path, sess)

        cleaner = StationCleaner(raw_path, self.PROC_DIR)
        cleaned = cleaner.clean()
        if not cleaned:
            print("ℹ️ Cleaned CSV already exists, skipping")
            cleaned = self.PROC_DIR / "cleaned_station_data.csv"

        inserter = StationInserter(cleaned)
        count    = inserter.upsert()
        print(f"✓ Upserted {count} stations")
