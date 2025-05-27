from pyproj import Geod

# WGS84 ellipsoid parameter setting 
_geod = Geod(ellps="WGS84")

# Function to calculate the distance between two points

def calc_air_distance_p_to_p(point1, point2) -> float:

    """
    Calculate the distance between two points.  
    Points should be in the format of (longitude, latitude).
    """

    lon1, lat1 = point1
    lon2, lat2 = point2

    _, _, distance = _geod.inv(lon1, lat1, lon2, lat2)

    return(distance)
