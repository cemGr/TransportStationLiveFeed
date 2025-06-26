import time
from src.scraper.station.scraper import StationScraper

if __name__ == "__main__":
    scraper = StationScraper()
    while True:
        try:
            scraper.run_once()
        except Exception as exc:
            print("⚠️ Station Scraper Error", exc, flush=True)
        time.sleep(60*60)
