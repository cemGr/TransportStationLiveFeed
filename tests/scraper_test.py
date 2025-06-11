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


def test_extract_trip_zip_auto_cleans_station(tmp_path, monkeypatch):
    trip_csv = (
        "trip_id,duration,start_time,end_time,start_station,start_lat,start_lon,end_station,end_lat,end_lon,bike_id,plan_duration,trip_route_category,passholder_type,bike_type\n"
        "1,5,2024-01-01 00:00:00,2024-01-01 00:05:00,1,52.0,13.0,2,52.1,13.1,100,5,Loop,Monthly,standard\n"
    )
    station_csv = (
        "Kiosk ID,Kiosk Name,Go Live Date,Region ,Status,Latitude,Longitude,status2\n"
        "1,One,2020-01-01,RegionA,Active,52,13,ok\n"
    )
    zip_path = tmp_path / "trips.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("trips.csv", trip_csv)
        zf.writestr("metro-bike-share-stations-2024-01-01.csv", station_csv)

    dest = tmp_path / "out"
    dest.mkdir()

    import src.scraper.scraper as sc
    sc.STATIC_DIR = tmp_path / "static"
    sc.TRIP_DIR = tmp_path / "proc"
    sc.STATIC_DIR.mkdir()
    sc.TRIP_DIR.mkdir()

    class DummyConn:
        def close(self):
            pass

    monkeypatch.setattr(sc, "open_connection", lambda: DummyConn())
    monkeypatch.setattr(sc, "insert_trips_from_csv", lambda p, c: None)

    extract_trip_zip(dest, zip_path)

    assert (sc.STATIC_DIR / "cleaned_station_data.csv").exists()
    assert (sc.TRIP_DIR / "trips.clean.csv").exists()


def test_extract_trip_zip_handles_clean_errors(tmp_path, monkeypatch, capsys):
    """A broken station table should not crash extraction."""
    trip_csv = (
        "duration,start_time,end_time,start_station,start_lat,start_lon," \
        "end_station,end_lat,end_lon,bike_id,bike_type\n" \
        "5,2024-01-01 00:00:00,2024-01-01 00:05:00,1,52.0,13.0,2,52.1,13.1,100,standard\n"
    )
    station_csv = "bad,data\n1,2\n"
    zip_path = tmp_path / "broken.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("trips.csv", trip_csv)
        zf.writestr("metro-bike-share-stations-2024-01-01.csv", station_csv)

    dest = tmp_path / "out"
    dest.mkdir()

    import src.scraper.scraper as sc
    sc.STATIC_DIR = tmp_path / "static"
    sc.TRIP_DIR = tmp_path / "proc"
    sc.STATIC_DIR.mkdir()
    sc.TRIP_DIR.mkdir()

    monkeypatch.setattr(sc, "open_connection", lambda: None)
    monkeypatch.setattr(sc, "insert_trips_from_csv", lambda p, c: None)

    extract_trip_zip(dest, zip_path)

    out = capsys.readouterr().out
    assert "failed to clean station data" in out
    assert (dest / "trips.csv").exists()
