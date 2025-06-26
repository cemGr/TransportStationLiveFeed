from core.base import Base
from sqlalchemy import Column, Integer, Boolean, sql, DateTime, func


class WeatherCheckpoint(Base):
    """
    A single-row table that remembers the next coordinate index
    the WeatherScraper should start with.
    """
    __tablename__ = "weather_checkpoint"

    id = Column(
        Boolean,
        primary_key=True,
        default=True,
        server_default=sql.expression.true(),
    )

    last_coord_index = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<WeatherCheckpoint idx={self.last_coord_index} "
            f"updated_at={self.updated_at:%Y-%m-%d %H:%M:%S}>"
        )