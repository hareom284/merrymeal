import math

from apps.core.geo import haversine_km


def test_haversine_known_distance_melbourne_to_sydney():
    melbourne = (-37.8136, 144.9631)
    sydney = (-33.8688, 151.2093)
    distance = haversine_km(*melbourne, *sydney)
    assert math.isclose(distance, 713, abs_tol=5)


def test_haversine_zero_distance():
    assert haversine_km(0.0, 0.0, 0.0, 0.0) == 0.0
