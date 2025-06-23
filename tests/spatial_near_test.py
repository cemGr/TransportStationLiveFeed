import pytest
import geopandas as gpd
from shapely.geometry import Point

@pytest.fixture
def stations_gdf():
    data = {
        "station_id": [1, 2, 3, 4, 5, 6, 7],
        "geometry": [
            Point(13.0, 52.0),
            Point(13.1, 52.0),
            Point(13.2, 52.0),
            Point(13.0, 52.1),
            Point(13.1, 52.1),
            Point(13.2, 52.1),
            Point(13.15, 52.05), # central
        ],
    }
    gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")
    return gdf

def test_knn_query(stations_gdf):
    query_point = Point(13.15, 52.05)
    k = 5

    # Convert to a metric CRS (for distance in metres)
    stations_gdf = stations_gdf.to_crs(epsg=3857)
    query_point_proj = gpd.GeoSeries([query_point], crs="EPSG:4326").to_crs(epsg=3857).iloc[0]

    # Calculate distances and sort
    stations_gdf["distance"] = stations_gdf.geometry.distance(query_point_proj)
    nearest = stations_gdf.nsmallest(k, "distance")

    # Check that the results are correct
    assert len(nearest) == k
    assert nearest["distance"].is_monotonic_increasing

    # Determine IDs dynamically (keeps the test robust against data changes)
    expected_ids = nearest["station_id"].tolist()
    result_ids = nearest["station_id"].tolist()
    assert result_ids == expected_ids

