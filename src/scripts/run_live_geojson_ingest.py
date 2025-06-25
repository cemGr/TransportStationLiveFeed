import time
from src.scraper.live_geojson.scraper import LiveGeoJSONScraper

if __name__ == "__main__":
    scraper = LiveGeoJSONScraper()
    while True:
        try:
            scraper.run_once()
        except Exception as exc:
            print("⚠ LiveGeoJSONScraper failed:", exc, flush=True)
        time.sleep(60)  # every minute
