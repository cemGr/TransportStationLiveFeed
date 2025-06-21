DATA_PAGE      = "https://bikeshare.metro.net/about/data/"
GEOJSON_URL    = "https://bikeshare.metro.net/stations/stations.geojson"
STATION_RE_CSV = r"metro-bike-share.*new_project_src.*\.csv$"
TRIP_RE_ZIP    = r"trips?.*\.zip$"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": DATA_PAGE,
}
TIMEOUT = 30

# weather
API_URL          = "https://archive-api.open-meteo.com/v1/archive"
BATCH_SIZE       = 50
TRIP_BATCH_SIZE  = 60000