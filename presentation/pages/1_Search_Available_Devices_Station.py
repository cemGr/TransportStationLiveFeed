import sys
from pathlib import Path

# Ensure the repository root is on the import path so absolute imports work
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from presentation.common import station_search_page
from usecases.stations import find_nearest_stations

station_search_page(
    title="\U0001f6b2 Available stations with bikes nearby",
    state_key="nearest_bikes",
    search_func=find_nearest_stations,
    result_col="num_bikes",
    value_label="Bikes",
    icon_color="blue",
)
