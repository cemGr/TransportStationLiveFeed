INSERT INTO public.stations
  (station_id, name, longitude, latitude, num_bikes, num_docks, online, geom)
VALUES
  (1,  'Alexanderplatz',       13.4125, 52.5234,  8, 12, TRUE,
    ST_SetSRID(ST_MakePoint(13.4125, 52.5234), 4326)::GEOGRAPHY),
  (2,  'Hauptbahnhof',         13.3695, 52.5251, 12,  4, TRUE,
    ST_SetSRID(ST_MakePoint(13.3695, 52.5251), 4326)::GEOGRAPHY),
  (3,  'Potsdamer Platz',      13.3754, 52.5096,  3,  9, FALSE,
    ST_SetSRID(ST_MakePoint(13.3754, 52.5096), 4326)::GEOGRAPHY),
  (4,  'Friedrichstraße',      13.3889, 52.5208,  0, 15, TRUE,
    ST_SetSRID(ST_MakePoint(13.3889, 52.5208), 4326)::GEOGRAPHY),
  (5,  'Gleisdreieck',         13.3661, 52.4993,  5, 10, TRUE,
    ST_SetSRID(ST_MakePoint(13.3661, 52.4993), 4326)::GEOGRAPHY),
  (6,  'Schlesisches Tor',     13.4356, 52.4990,  2, 12, FALSE,
    ST_SetSRID(ST_MakePoint(13.4356, 52.4990), 4326)::GEOGRAPHY),
  (7,  'Zoologischer Garten',  13.3373, 52.5076, 10,  8, TRUE,
    ST_SetSRID(ST_MakePoint(13.3373, 52.5076), 4326)::GEOGRAPHY),
  (8,  'Kottbusser Tor',       13.4204, 52.4990,  7,  7, TRUE,
    ST_SetSRID(ST_MakePoint(13.4204, 52.4990), 4326)::GEOGRAPHY),
  (9,  'Oberbaumbrücke',       13.4407, 52.5000,  4, 11, FALSE,
    ST_SetSRID(ST_MakePoint(13.4407, 52.5000), 4326)::GEOGRAPHY),
  (10, 'Senefelderplatz',      13.4128, 52.5301,  6, 14, TRUE,
    ST_SetSRID(ST_MakePoint(13.4128, 52.5301), 4326)::GEOGRAPHY);