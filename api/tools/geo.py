"""Deterministic distance and targeting; no assertion about flood arrival or safety."""
from math import asin, cos, isfinite, radians, sin, sqrt


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    for lat, lng in ((lat1, lng1), (lat2, lng2)):
        if not isfinite(lat) or not isfinite(lng) or not -90 <= lat <= 90 or not -180 <= lng <= 180:
            raise ValueError('Invalid coordinates')
    dlat, dlng = radians(lat2-lat1), radians(lng2-lng1)
    value = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlng/2)**2
    return 6_371_008.8 * 2 * asin(sqrt(min(1, max(0, value))))
