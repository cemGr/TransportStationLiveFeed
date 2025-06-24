import sys
from pathlib import Path

# Ensure the repository root is on the import path so absolute imports work
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from presentation.common import station_search_page
from usecases.stations import find_nearest_docks

station_search_page(
    title="\U0001f68f Available stations with free docks nearby",
    state_key="nearest_docks",
    search_func=find_nearest_docks,
    result_col="num_docks",
    value_label="Docks",
    icon_color="green",
)
