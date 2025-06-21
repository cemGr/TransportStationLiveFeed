from sqlalchemy import Column, Integer, String, Float, Boolean
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from geoalchemy2 import Geography
from sqlalchemy.orm import relationship

from core.db import Base

class Station(Base):
    __tablename__ = "stations"

    station_id = Column(Integer, primary_key=True)
    name = Column(String)
    longitude = Column(DOUBLE_PRECISION)
    latitude = Column(DOUBLE_PRECISION)
    num_bikes = Column(Integer)
    num_docks = Column(Integer)
    online = Column(Boolean, nullable=False)
    geom = Column(Geography(geometry_type="POINT", srid=4326))

    live_statuses = relationship(
        "LiveStationStatus",
        back_populates="station",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    def __repr__(self):
        return f"<Station(id={self.station_id}, name={self.name})>"