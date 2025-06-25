from typing import ClassVar

from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from geoalchemy2 import Geometry
from sqlalchemy.orm import relationship

from core.base import Base

class Station(Base):
    __tablename__ = "stations"

    station_id = Column(Integer, primary_key=True)
    name = Column(String)
    longitude = Column(DOUBLE_PRECISION)
    latitude = Column(DOUBLE_PRECISION)
    geom = Column(Geometry(geometry_type="POINT", srid=4326))

    distance_m: ClassVar[float | None] = None
    num_bikes: ClassVar[int | None] = None
    num_docks: ClassVar[int | None] = None
    online: ClassVar[bool | None] = None

    live_statuses = relationship(
        "LiveStationStatus",
        back_populates="station",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    def __repr__(self):
        return f"<Station(id={self.station_id}, name={self.name})>"