"""Unit tests for place reverse-geocoding parsing and display labels."""

from __future__ import annotations

import unittest

from app.services.location.geocoding_service import (
    build_place_display_label,
    parse_reverse_geocode_result,
)


class PlaceGeocodingServiceTests(unittest.TestCase):
    def test_parse_reverse_geocode_maps_required_fields(self) -> None:
        payload = {
            "status": "OK",
            "results": [
                {
                    "formatted_address": "123 Main St, Vista, CA 92084, USA",
                    "address_components": [
                        {"long_name": "123", "short_name": "123", "types": ["street_number"]},
                        {"long_name": "Main Street", "short_name": "Main St", "types": ["route"]},
                        {"long_name": "Vista", "short_name": "Vista", "types": ["locality", "political"]},
                        {
                            "long_name": "San Diego County",
                            "short_name": "San Diego County",
                            "types": ["administrative_area_level_2", "political"],
                        },
                        {
                            "long_name": "California",
                            "short_name": "CA",
                            "types": ["administrative_area_level_1", "political"],
                        },
                        {"long_name": "United States", "short_name": "US", "types": ["country", "political"]},
                    ],
                }
            ],
        }

        result = parse_reverse_geocode_result(payload)

        self.assertEqual(result.formatted_address, "123 Main St, Vista, CA 92084, USA")
        self.assertEqual(result.street, "123 Main Street")
        self.assertEqual(result.city, "Vista")
        self.assertEqual(result.county, "San Diego County")
        self.assertEqual(result.state, "California")
        self.assertEqual(result.country, "United States")
        self.assertEqual(result.country_code, "US")

    def test_city_fallback_priority(self) -> None:
        payload = {
            "status": "OK",
            "results": [
                {
                    "formatted_address": "London, UK",
                    "address_components": [
                        {"long_name": "Westminster", "short_name": "Westminster", "types": ["sublocality"]},
                        {"long_name": "London", "short_name": "London", "types": ["postal_town"]},
                        {
                            "long_name": "England",
                            "short_name": "ENG",
                            "types": ["administrative_area_level_1", "political"],
                        },
                        {"long_name": "United Kingdom", "short_name": "GB", "types": ["country", "political"]},
                    ],
                }
            ],
        }

        result = parse_reverse_geocode_result(payload)
        self.assertEqual(result.city, "London")

    def test_display_label_priority_uses_city_state(self) -> None:
        label = build_place_display_label(
            city="Vista",
            state="California",
            country="United States",
            country_code="US",
            formatted_address="123 Main St, Vista, CA 92084, USA",
            latitude=33.20,
            longitude=-117.24,
        )
        self.assertEqual(label, "Vista, CA")

    def test_display_label_falls_back_to_formatted_address_then_coordinates(self) -> None:
        label_from_address = build_place_display_label(
            city=None,
            state=None,
            country=None,
            country_code=None,
            formatted_address="Some Address",
            latitude=47.61,
            longitude=-122.33,
        )
        self.assertEqual(label_from_address, "Some Address")

        label_from_coords = build_place_display_label(
            city=None,
            state=None,
            country=None,
            country_code=None,
            formatted_address=None,
            latitude=47.61,
            longitude=-122.33,
        )
        self.assertEqual(label_from_coords, "47.61, -122.33")


if __name__ == "__main__":
    unittest.main()
