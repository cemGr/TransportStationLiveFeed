from sqlalchemy import func
from geoalchemy2.functions import ST_DistanceSphere
from core.db import get_session
from new_project_src.models.station import Station

def nearest_stations_with_docks(
    latitude: float, longitude: float, k: int = 5
) -> list[Station]:
    """
    Return up to k Station objects (online, with >0 docks), sorted by distance.
    Each Station will have a .distance_m attribute set.
    """
    with get_session() as session:
        pt = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
        query = (
            session.query(
                Station,
                ST_DistanceSphere(Station.geom, pt).label("distance_m"),
            )
            .filter(Station.online.is_(True), Station.num_docks > 0)
            .order_by(func.ST_DistanceSphere(Station.geom, pt))
            .limit(k)
        )
        results = query.all()

    stations: list[Station] = []
    for station, dist in results:
        setattr(station, "distance_m", float(dist))
        stations.append(station)
    return stations
