import zipfile

from src.scraper.scraper import extract_trip_zip


def test_extract_trip_zip_warns_without_station_data(tmp_path, capsys):
    csv = (
        "duration,start_time,end_time,start_station,start_lat,start_lon,"
        "end_station,end_lat,end_lon,bike_id,bike_type\n"
        "5,2024-01-01 00:00:00,2024-01-01 00:05:00,1,52.0,13.0,2,52.1,13.1,100,standard\n"
    )
    zip_path = tmp_path / "trips.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("trips.csv", csv)

    dest = tmp_path / "out"
    dest.mkdir()

    # setup required globals
    import src.scraper.scraper as sc
    sc.STATIC_DIR = tmp_path / "static"
    sc.TRIP_DIR = tmp_path / "proc"
    sc.STATIC_DIR.mkdir()
    sc.TRIP_DIR.mkdir()

    extract_trip_zip(dest, zip_path)

    assert (dest / "trips.csv").exists()
    assert "cleaned station data missing" in capsys.readouterr().out

