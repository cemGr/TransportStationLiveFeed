import pytest
from src.distance import calc_air_distance_p_to_p


class TestAirDistances:
    def test_zero_distance(self):
        assert calc_air_distance_p_to_p((0, 0), (0, 0)) == 0

    def test_known_distance(self):
        berlin_lon, berlin_lat = 13.404954, 52.520008
        paris_lon, paris_lat = 2.352222, 48.856613
        expected_distance = 879694.663
        distance = calc_air_distance_p_to_p((berlin_lon, berlin_lat), (paris_lon, paris_lat))
        assert abs(distance - expected_distance) < 1


