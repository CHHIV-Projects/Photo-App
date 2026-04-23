"""Unit tests for deterministic place grouping helpers."""

from __future__ import annotations

import unittest

from app.models.place import Place
from app.services.places.grouping import (
    _find_first_matching_place,
    _haversine_meters,
    _is_valid_gps_pair,
)


class PlaceGroupingServiceTests(unittest.TestCase):
    def test_haversine_distance_zero_for_same_coordinate(self) -> None:
        distance = _haversine_meters(47.60621, -122.332071, 47.60621, -122.332071)
        self.assertAlmostEqual(distance, 0.0, places=6)

    def test_find_first_matching_place_includes_boundary(self) -> None:
        seed_place = Place(place_id=10, representative_latitude=47.60621, representative_longitude=-122.332071)
        # Approx ~100m north from seed place.
        probe_lat = 47.6071083
        probe_lon = -122.332071
        boundary = _haversine_meters(
            seed_place.representative_latitude,
            seed_place.representative_longitude,
            probe_lat,
            probe_lon,
        )

        matched = _find_first_matching_place(
            [seed_place],
            latitude=probe_lat,
            longitude=probe_lon,
            radius_meters=boundary,
        )

        self.assertIsNotNone(matched)
        assert matched is not None
        self.assertEqual(matched.place_id, 10)

    def test_find_first_matching_place_respects_input_order(self) -> None:
        place_a = Place(place_id=1, representative_latitude=47.60621, representative_longitude=-122.332071)
        place_b = Place(place_id=2, representative_latitude=47.60622, representative_longitude=-122.33208)

        matched = _find_first_matching_place(
            [place_a, place_b],
            latitude=47.606215,
            longitude=-122.332075,
            radius_meters=100.0,
        )

        self.assertIsNotNone(matched)
        assert matched is not None
        self.assertEqual(matched.place_id, 1)

    def test_gps_validation_rejects_partial_out_of_range_and_zero_zero(self) -> None:
        self.assertFalse(_is_valid_gps_pair(None, -122.0))
        self.assertFalse(_is_valid_gps_pair(47.0, None))
        self.assertFalse(_is_valid_gps_pair(120.0, -122.0))
        self.assertFalse(_is_valid_gps_pair(47.0, -190.0))
        self.assertFalse(_is_valid_gps_pair(0.0, 0.0))
        self.assertTrue(_is_valid_gps_pair(47.60621, -122.332071))


if __name__ == "__main__":
    unittest.main()
