from sqlalchemy import func
from geoalchemy2.functions import ST_DistanceSphere
from core.db import get_session
from src.models import LiveStationStatus
from src.models.location import Location
from src.models.station import Station


def nearest_stations_with_docks(
        location: Location, k: int = 5, stations_with_missing_live_data: bool = False
) -> list[Station]:
    """
    Return up to k Station objects (online, with >0 docks), sorted by distance.
    Each Station will have a .distance_m attribute set.
    """
    with get_session() as session:
        pt = func.ST_SetSRID(func.ST_MakePoint(location.longitude, location.latitude), 4326)
        query = (
            session.query(
                Station,
                LiveStationStatus.num_bikes,
                LiveStationStatus.num_docks,
                LiveStationStatus.online,
                ST_DistanceSphere(Station.geom, pt).label("distance_m"),
            )
            .outerjoin(
                LiveStationStatus,
                LiveStationStatus.station_id == Station.station_id,
            )
            .order_by(ST_DistanceSphere(Station.geom, pt))
        )

        if not stations_with_missing_live_data:
            query = query.filter(
                LiveStationStatus.online.is_(True),
                LiveStationStatus.num_bikes > 0,
            )
        else:
            query = query.filter(
                (LiveStationStatus.station_id.is_(None)) |
                ((LiveStationStatus.online.is_(True)) & (LiveStationStatus.num_bikes > 0))
            )

        rows = query.limit(k).all()

    stations: list[Station] = []
    for station, bikes, docks, online, dist in rows:
        setattr(station, "num_bikes", bikes)
        setattr(station, "num_docks", docks)
        setattr(station, "online", online)
        setattr(station, "distance_m", float(dist))
        stations.append(station)
    return stations
