from sqlalchemy import Column, Integer, Boolean, TIMESTAMP, func, ForeignKey
from sqlalchemy.orm import relationship

from core.base import Base


class LiveStationStatus(Base):
    __tablename__ = "live_station_status"

    # → ForeignKey into your static stations table
    station_id = Column(
        Integer,
        ForeignKey("stations.station_id", ondelete="CASCADE"),
        primary_key=True,
    )

    num_bikes  = Column(Integer, nullable=False)
    num_docks  = Column(Integer, nullable=False)
    online     = Column(Boolean, nullable=False)

    # timestamp of this snapshot
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ↔ relationship back to static Station
    station = relationship(
        "Station",
        back_populates="live_statuses",
        lazy="joined",
    )

    def __repr__(self):
        return (
            f"<LiveStationStatus(station_id={self.station_id}, "
            f"bikes={self.num_bikes}, docks={self.num_docks}, online={self.online})>"
        )
