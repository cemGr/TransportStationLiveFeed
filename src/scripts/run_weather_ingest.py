import time
from src.scraper.weather.scraper import WeatherScraper

if __name__ == "__main__":
    weather_scraper = WeatherScraper()
    while True:
        try:
            weather_scraper.run_once()
        except Exception as e:
            print("⚠️ WeatherScraper error:", e, flush=True)
        time.sleep(24 * 3600)