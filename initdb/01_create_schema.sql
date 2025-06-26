-- stations table
CREATE TABLE public.stations
(
    station_id INTEGER PRIMARY KEY,
    name       TEXT,
    longitude  DOUBLE PRECISION,
    latitude   DOUBLE PRECISION,
    geom       GEOMETRY(Point, 4326)
);

-- trips table with bike_id as TEXT and foreign-keys
CREATE TABLE public.trips
(
    id            SERIAL PRIMARY KEY,
    duration      INTEGER,
    start_time    TIMESTAMP,
    end_time      TIMESTAMP,
    start_station INTEGER REFERENCES public.stations (station_id) ON DELETE SET NULL,
    start_lat     DOUBLE PRECISION,
    start_lon     DOUBLE PRECISION,
    end_station   INTEGER REFERENCES public.stations (station_id) ON DELETE SET NULL,
    end_lat       DOUBLE PRECISION,
    end_lon       DOUBLE PRECISION,
    bike_id       INTEGER,
    bike_type     TEXT
);

-- live snapshots
CREATE TABLE public.live_station_status
(
    station_id INTEGER PRIMARY KEY
        REFERENCES public.stations (station_id) ON DELETE CASCADE,
    num_bikes  INTEGER     NOT NULL,
    num_docks  INTEGER     NOT NULL,
    online     BOOLEAN     NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- weather aggregates
CREATE TABLE public.station_weather
(
    slot_ts        TIMESTAMP NOT NULL,
    station_id     INTEGER   NOT NULL REFERENCES public.stations (station_id),
    bikes_taken    INTEGER,
    bikes_returned INTEGER,
    lat            DOUBLE PRECISION,
    lon            DOUBLE PRECISION,
    cluster_id     INTEGER,
    temperature_2m REAL,
    temp_class     TEXT,
    rain_mm        REAL,
    is_raining     BOOLEAN,
    weather_code   INTEGER,
    season         TEXT,
    PRIMARY KEY (slot_ts, station_id)
);

CREATE INDEX ON public.stations USING GIST (geom);
CREATE INDEX ON public.live_station_status USING GIST (
    ST_SetSRID(ST_MakePoint(0,0),4326)
    );

CREATE TABLE public.weather_checkpoint
(
    id               BOOLEAN PRIMARY KEY  DEFAULT TRUE,
    last_coord_index INTEGER     NOT NULL DEFAULT 0,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);