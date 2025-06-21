import time
from new_project_src.scraper.weather.scraper import WeatherScraper

if __name__ == "__main__":
    ws = WeatherScraper()
    while True:
        try:
            ws.run_once()
        except Exception as e:
            print("⚠ WeatherScraper error:", e, flush=True)
        time.sleep(10 * 60)   # every 10 minutes