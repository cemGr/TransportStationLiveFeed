CREATE TABLE public.stations (
  station_id   INTEGER PRIMARY KEY,
  name         TEXT,
  longitude    DOUBLE PRECISION,
  latitude     DOUBLE PRECISION,
  num_bikes    INTEGER,
  num_docks    INTEGER,
  online       BOOLEAN NOT NULL,                     -- new column
  geom         GEOGRAPHY(Point, 4326)
);

CREATE TABLE public.trips (
  id            SERIAL PRIMARY KEY,
  duration      INTEGER,
  start_time    TIMESTAMP,
  end_time      TIMESTAMP,
  start_station INTEGER,
  start_lat     DOUBLE PRECISION,
  start_lon     DOUBLE PRECISION,
  end_station   INTEGER,
  end_lat       DOUBLE PRECISION,
  end_lon       DOUBLE PRECISION,
  bike_id       INTEGER,
  bike_type     TEXT
);
