from __future__ import annotations
import re
import zipfile
import shutil
from pathlib import Path
import requests

from src.bikemetro.constants import HEADERS, TRIP_RE_ZIP
from src.bikemetro.helpers import get_soup, stream_download
from src.scraper.trip.cleaner   import TripCleaner
from src.scraper.trip.inserter  import TripInserter


class TripScraper:
    STATION_SNAPSHOT_DIR = Path("/app/data/processed/station")
    TRIP_ZIP_DIR         = Path("/app/data/raw/trip")
    TRIP_CLEAN_DIR       = Path("/app/data/processed/trip")

    def __init__(self):
        self.STATION_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        self.TRIP_ZIP_DIR.mkdir(parents=True, exist_ok=True)
        self.TRIP_CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    def run_once(self):
        self._ensure_latest_station_csv()

        with requests.Session() as sess:
            sess.headers.update(HEADERS)
            soup = get_soup(sess)
            links = {
                a["href"]
                for a in soup.select("a[href]")
                if re.search(TRIP_RE_ZIP, a["href"], re.I)
            }

            processed, skipped = 0, 0
            for url in sorted(links, reverse=True):
                zip_path = self.TRIP_ZIP_DIR / Path(url).name
                if zip_path.exists():
                    skipped += 1
                else:
                    stream_download(url, zip_path, sess)
                    processed += 1

                self._extract_and_load(zip_path)

            print(f"Trip-data archives → new: {processed}, already present: {skipped}")

    def _ensure_latest_station_csv(self) -> Path:

        cleaned_station = self.STATION_SNAPSHOT_DIR / "cleaned_station_data.csv"
        if cleaned_station.exists():
            return cleaned_station

        from src.scraper.station.scraper import StationScraper   # local import avoids circularity
        StationScraper().run_once()
        return cleaned_station

    def _extract_and_load(self, zip_path: Path):
        station_csv = self.STATION_SNAPSHOT_DIR / "cleaned_station_data.csv"

        with zipfile.ZipFile(zip_path) as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                name = Path(member.filename).name

                if member.filename.startswith("__MACOSX/") or name.startswith("._"):
                    continue
                if not name.lower().endswith(".csv"):
                    continue

                raw_csv = self.TRIP_ZIP_DIR / name
                if not raw_csv.exists():
                    with zf.open(member) as src, open(raw_csv, "wb") as out:
                        shutil.copyfileobj(src, out)

                cleaner  = TripCleaner(raw_csv, station_csv, self.TRIP_CLEAN_DIR)
                cleaned  = cleaner.clean()
                if not cleaned:
                    continue

                inserter = TripInserter(cleaned)
                rows     = inserter.insert()
                print(f"→ {rows} rows inserted from {cleaned.name}")

                raw_csv.unlink(missing_ok=True)
