import time
from new_project_src.scraper.station.scraper import StationScraper

if __name__ == "__main__":
    scraper = StationScraper()
    while True:
        try:
            scraper.run_once()
        except Exception as exc:
            print("⚠", exc, flush=True)
        time.sleep(60*60)        # run hourly
