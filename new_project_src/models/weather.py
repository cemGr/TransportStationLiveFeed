from sqlalchemy import Column, Integer, Float, String, Boolean, TIMESTAMP
from core.db import Base

class StationWeather(Base):
    __tablename__ = "station_weather"

    slot_ts = Column(TIMESTAMP, primary_key=True)
    station_id = Column(Integer, primary_key=True)

    bikes_taken = Column(Integer)
    bikes_returned = Column(Integer)
    lat = Column(Float)
    lon = Column(Float)
    cluster_id = Column(Integer)

    temperature_2m = Column(Float)
    temp_class = Column(String)
    rain_mm = Column(Float)
    is_raining = Column(Boolean)
    weather_code = Column(Integer)
    season = Column(String)