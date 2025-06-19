CREATE TABLE public.station_weather (
    slot_ts        TIMESTAMP NOT NULL,
    station_id     INTEGER NOT NULL,
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
