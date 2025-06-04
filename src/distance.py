from math import atan, atan2, cos, sin, sqrt, tan, radians

# WGS84 ellipsoid constants
_WGS84_A = 6378137.0
_WGS84_F = 1 / 298.257223563
_WGS84_B = (1 - _WGS84_F) * _WGS84_A


def calc_air_distance_p_to_p(point1, point2) -> float:
    """Return the geodesic distance in meters between two lon/lat points."""
    lon1, lat1 = map(radians, point1)
    lon2, lat2 = map(radians, point2)

    U1 = atan((1 - _WGS84_F) * tan(lat1))
    U2 = atan((1 - _WGS84_F) * tan(lat2))
    L = lon2 - lon1
    lam = L

    for _ in range(200):
        sin_sigma = sqrt((cos(U2) * sin(lam)) ** 2 + (
            cos(U1) * sin(U2) - sin(U1) * cos(U2) * cos(lam)
        ) ** 2)
        if sin_sigma == 0:
            return 0.0
        cos_sigma = sin(U1) * sin(U2) + cos(U1) * cos(U2) * cos(lam)
        sigma = atan2(sin_sigma, cos_sigma)
        sin_alpha = cos(U1) * cos(U2) * sin(lam) / sin_sigma
        cos2_alpha = 1 - sin_alpha ** 2
        cos2_sigma_m = 0 if cos2_alpha == 0 else cos_sigma - 2 * sin(U1) * sin(U2) / cos2_alpha
        C = _WGS84_F / 16 * cos2_alpha * (4 + _WGS84_F * (4 - 3 * cos2_alpha))
        lam_prev = lam
        lam = L + (1 - C) * _WGS84_F * sin_alpha * (
            sigma + C * sin_sigma * (
                cos2_sigma_m + C * cos_sigma * (-1 + 2 * cos2_sigma_m ** 2)
            )
        )
        if abs(lam - lam_prev) < 1e-12:
            break
    u2 = cos2_alpha * (_WGS84_A ** 2 - _WGS84_B ** 2) / (_WGS84_B ** 2)
    A = 1 + u2 / 16384 * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)))
    B = u2 / 1024 * (256 + u2 * (-128 + u2 * (74 - 47 * u2)))
    delta_sigma = B * sin_sigma * (
        cos2_sigma_m
        + B / 4 * (
            cos_sigma * (-1 + 2 * cos2_sigma_m ** 2)
            - B / 6 * cos2_sigma_m * (-3 + 4 * sin_sigma ** 2) * (-3 + 4 * cos2_sigma_m ** 2)
        )
    )
    return _WGS84_B * A * (sigma - delta_sigma)

