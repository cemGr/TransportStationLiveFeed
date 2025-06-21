from sqlalchemy import Column, Integer, Float, String, TIMESTAMP
from core.db import Base

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True)
    duration = Column(Integer)
    start_time = Column(TIMESTAMP)
    end_time = Column(TIMESTAMP)
    start_station = Column(Integer)
    start_lat = Column(Float)
    start_lon = Column(Float)
    end_station = Column(Integer)
    end_lat = Column(Float)
    end_lon = Column(Float)
    bike_id = Column(String)
    bike_type = Column(String, nullable=True)