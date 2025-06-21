from __future__ import annotations
import re, zipfile, shutil
from pathlib import Path
import requests

from new_project_src.bikemetro.constants import DATA_PAGE, HEADERS, TIMEOUT, TRIP_RE_ZIP
from new_project_src.bikemetro.helpers import get_soup, stream_download
from new_project_src.scraper.station.cleaner import StationCleaner           # ensure station table exists
from new_project_src.scraper.trip.cleaner   import TripCleaner
from new_project_src.scraper.trip.inserter  import TripInserter


class TripScraper:
    """
    Download *all* zip archives listed on the Metro *Data* page that match
    `TRIP_RE_ZIP`, extract their CSVs, clean & load them into Postgres.

    - Each ZIP often holds multiple months.
    - Already-processed zips are skipped (idempotent).
    - Station table is refreshed first if missing (required for coord impute).
    """

    STATION_SNAPSHOT_DIR = Path("/app/data/processed/station")
    TRIP_ZIP_DIR         = Path("/app/data/raw/trip")
    TRIP_CLEAN_DIR       = Path("/app/data/processed/trip")

    def __init__(self):
        self.STATION_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        self.TRIP_ZIP_DIR.mkdir(parents=True, exist_ok=True)
        self.TRIP_CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    # ────────────────────────────────────────────────────────────────────────
    def run_once(self):
        # 1. ensure station table exists
        self._ensure_latest_station_csv()

        # 2. crawl the Data page
        with requests.Session() as sess:
            sess.headers.update(HEADERS)
            soup = get_soup(sess)
            links = {
                a["href"]
                for a in soup.select("a[href]")
                if re.search(TRIP_RE_ZIP, a["href"], re.I)
            }

            processed, skipped = 0, 0
            for url in sorted(links, reverse=True):        # newest first
                zip_path = self.TRIP_ZIP_DIR / Path(url).name
                if zip_path.exists():
                    skipped += 1
                else:
                    stream_download(url, zip_path, sess)
                    processed += 1

                self._extract_and_load(zip_path)

            print(f"Trip-data archives → new: {processed}, already present: {skipped}")

    # ────────────────────────────────────────────────────────────────────────
    # helpers
    def _ensure_latest_station_csv(self) -> Path:
        """
        If *cleaned_station_data.csv* is absent, run the StationScraper once
        (otherwise TripCleaner cannot impute coordinates).
        """
        cleaned_station = self.STATION_SNAPSHOT_DIR / "cleaned_station_data.csv"
        if cleaned_station.exists():
            return cleaned_station

        from new_project_src.scraper.station.scraper import StationScraper   # local import avoids circularity
        StationScraper().run_once()
        return cleaned_station

    def _extract_and_load(self, zip_path: Path):
        """
        Extract each **trip CSV** inside *zip_path*, clean it, insert rows,
        then delete the raw CSV to save disk.
        """
        station_csv = self.STATION_SNAPSHOT_DIR / "cleaned_station_data.csv"

        with zipfile.ZipFile(zip_path) as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                name = Path(member.filename).name
                # Ignore macOS artefacts
                if member.filename.startswith("__MACOSX/") or name.startswith("._"):
                    continue
                if not name.lower().endswith(".csv"):
                    continue

                # write raw csv
                raw_csv = self.TRIP_ZIP_DIR / name
                if not raw_csv.exists():
                    with zf.open(member) as src, open(raw_csv, "wb") as out:
                        shutil.copyfileobj(src, out)

                # clean ➞ insert
                cleaner  = TripCleaner(raw_csv, station_csv, self.TRIP_CLEAN_DIR)
                cleaned  = cleaner.clean()
                if not cleaned:
                    continue          # already processed

                inserter = TripInserter(cleaned)
                rows     = inserter.insert()
                print(f"→ {rows} rows inserted from {cleaned.name}")

                # optional: delete raw csv to reclaim space
                raw_csv.unlink(missing_ok=True)
