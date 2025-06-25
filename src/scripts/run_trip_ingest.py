import time
import traceback

from src.scraper.trip.scraper import TripScraper

if __name__ == "__main__":
    scraper = TripScraper()
    while True:
        try:
            scraper.run_once()
        except Exception as exc:
            print("⚠ TripScraper failed:", exc, flush=True)
            traceback.print_exc()
        time.sleep(24 * 3600)
