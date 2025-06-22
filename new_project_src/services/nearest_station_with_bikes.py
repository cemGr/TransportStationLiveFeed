from sqlalchemy import func
from geoalchemy2.functions import ST_DistanceSphere

from core.db import get_session
from new_project_src.models import LiveStationStatus
from new_project_src.models.station import Station
from new_project_src.models.location import Location


def nearest_stations_with_bikes(location: Location, k: int = 5) -> list[Station]:
    """
    Return up to k Station objects (online, with >0 bikes), sorted by distance.
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
            .join(  # ← tie into the live snapshot
                LiveStationStatus,
                LiveStationStatus.station_id == Station.station_id,
            )
            .filter(
                LiveStationStatus.online.is_(True),
                LiveStationStatus.num_bikes > 0,
            )
            .order_by(ST_DistanceSphere(Station.geom, pt))
            .limit(k)
        )
        rows = query.all()

    stations: list[Station] = []
    for station, bikes, docks, online, dist in rows:
        setattr(station, "num_bikes", bikes)
        setattr(station, "num_docks", docks)
        setattr(station, "online", online)
        setattr(station, "distance_m", float(dist))
        stations.append(station)
    return stations
