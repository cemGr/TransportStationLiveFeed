CREATE TABLE public.stations (
  station_id   INTEGER PRIMARY KEY,
  name         TEXT,
  longitude    DOUBLE PRECISION,
  latitude     DOUBLE PRECISION,
  num_bikes    INTEGER,
  num_docks    INTEGER,
  online       BOOLEAN NOT NULL,                     -- NEUE SPALTE
  geom         GEOGRAPHY(Point, 4326)
);