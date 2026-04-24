"""Unit tests for deterministic metadata canonicalization selectors."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from app.models.asset_metadata_observation import AssetMetadataObservation
from app.services.metadata.canonicalization_service import (
    _apply_gps_ref,
    _choose_best_camera_value,
    _choose_best_captured_at,
    _choose_best_dimensions,
    _choose_best_location,
)


class MetadataCanonicalizationServiceTests(unittest.TestCase):
    def _observation(
        self,
        *,
        obs_id: int,
        origin: str,
        captured_at: datetime | None,
        gps_latitude: float | None = None,
        gps_longitude: float | None = None,
        camera_make: str | None,
        camera_model: str | None,
        width: int | None,
        height: int | None,
        provenance_id: int | None,
        source_type: str | None = "local_folder",
        extension: str | None = ".jpg",
        is_legacy_seeded: bool = False,
    ) -> AssetMetadataObservation:
        return AssetMetadataObservation(
            id=obs_id,
            asset_sha256="asset-sha",
            provenance_id=provenance_id,
            observation_origin=origin,
            observed_source_path="C:/source/file.jpg",
            observed_source_type=source_type,
            observed_extension=extension,
            exif_datetime_original=None,
            exif_create_date=None,
            captured_at_observed=captured_at,
            gps_latitude=gps_latitude,
            gps_longitude=gps_longitude,
            camera_make=camera_make,
            camera_model=camera_model,
            width=width,
            height=height,
            is_legacy_seeded=is_legacy_seeded,
        )

    def test_choose_best_captured_at_prefers_provenance_and_valid_datetime(self) -> None:
        bad_placeholder = datetime(2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        chosen = datetime(2021, 6, 3, 12, 30, 0, tzinfo=timezone.utc)

        observations = [
            self._observation(
                obs_id=1,
                origin="legacy",
                captured_at=bad_placeholder,
                gps_latitude=None,
                gps_longitude=None,
                camera_make=None,
                camera_model=None,
                width=None,
                height=None,
                provenance_id=None,
                is_legacy_seeded=True,
            ),
            self._observation(
                obs_id=2,
                origin="vault",
                captured_at=datetime(2020, 6, 3, 12, 30, 0, tzinfo=timezone.utc),
                gps_latitude=None,
                gps_longitude=None,
                camera_make="Canon",
                camera_model="EOS",
                width=4000,
                height=3000,
                provenance_id=None,
            ),
            self._observation(
                obs_id=3,
                origin="provenance",
                captured_at=chosen,
                gps_latitude=None,
                gps_longitude=None,
                camera_make="Canon",
                camera_model="EOS",
                width=4000,
                height=3000,
                provenance_id=10,
                extension=".heic",
            ),
        ]

        self.assertEqual(_choose_best_captured_at(observations), chosen)

    def test_choose_best_camera_value_ignores_generic_placeholders(self) -> None:
        observations = [
            self._observation(
                obs_id=1,
                origin="provenance",
                captured_at=None,
                gps_latitude=None,
                gps_longitude=None,
                camera_make="Unknown",
                camera_model="N/A",
                width=None,
                height=None,
                provenance_id=5,
            ),
            self._observation(
                obs_id=2,
                origin="vault",
                captured_at=None,
                gps_latitude=None,
                gps_longitude=None,
                camera_make="FUJIFILM",
                camera_model="X-T5",
                width=None,
                height=None,
                provenance_id=None,
            ),
        ]

        self.assertEqual(_choose_best_camera_value(observations, "camera_make"), "FUJIFILM")
        self.assertEqual(_choose_best_camera_value(observations, "camera_model"), "X-T5")

    def test_choose_best_dimensions_prefers_largest_pixel_area(self) -> None:
        observations = [
            self._observation(
                obs_id=1,
                origin="provenance",
                captured_at=None,
                gps_latitude=None,
                gps_longitude=None,
                camera_make=None,
                camera_model=None,
                width=4032,
                height=3024,
                provenance_id=1,
                extension=".jpg",
            ),
            self._observation(
                obs_id=2,
                origin="provenance",
                captured_at=None,
                gps_latitude=None,
                gps_longitude=None,
                camera_make=None,
                camera_model=None,
                width=6000,
                height=4000,
                provenance_id=2,
                extension=".heic",
            ),
        ]

        self.assertEqual(_choose_best_dimensions(observations), (6000, 4000))

    def test_choose_best_location_prefers_most_frequent_normalized_pair(self) -> None:
        observations = [
            self._observation(
                obs_id=1,
                origin="provenance",
                captured_at=None,
                gps_latitude=40.7127764,
                gps_longitude=-74.0059741,
                camera_make=None,
                camera_model=None,
                width=None,
                height=None,
                provenance_id=10,
            ),
            self._observation(
                obs_id=2,
                origin="vault",
                captured_at=None,
                gps_latitude=40.71277649,
                gps_longitude=-74.00597409,
                camera_make=None,
                camera_model=None,
                width=None,
                height=None,
                provenance_id=None,
            ),
            self._observation(
                obs_id=3,
                origin="provenance",
                captured_at=None,
                gps_latitude=34.052235,
                gps_longitude=-118.243683,
                camera_make=None,
                camera_model=None,
                width=None,
                height=None,
                provenance_id=11,
            ),
        ]

        self.assertEqual(_choose_best_location(observations), (40.712776, -74.005974))

    def test_choose_best_location_tiebreak_prefers_origin_then_ids(self) -> None:
        observations = [
            self._observation(
                obs_id=7,
                origin="vault",
                captured_at=None,
                gps_latitude=35.0000004,
                gps_longitude=-80.0000004,
                camera_make=None,
                camera_model=None,
                width=None,
                height=None,
                provenance_id=None,
            ),
            self._observation(
                obs_id=3,
                origin="provenance",
                captured_at=None,
                gps_latitude=36.0,
                gps_longitude=-81.0,
                camera_make=None,
                camera_model=None,
                width=None,
                height=None,
                provenance_id=5,
            ),
        ]

        self.assertEqual(_choose_best_location(observations), (36.0, -81.0))

    def test_choose_best_location_ignores_invalid_and_zero_pairs(self) -> None:
        observations = [
            self._observation(
                obs_id=1,
                origin="provenance",
                captured_at=None,
                gps_latitude=0.0,
                gps_longitude=0.0,
                camera_make=None,
                camera_model=None,
                width=None,
                height=None,
                provenance_id=1,
            ),
            self._observation(
                obs_id=2,
                origin="provenance",
                captured_at=None,
                gps_latitude=120.0,
                gps_longitude=10.0,
                camera_make=None,
                camera_model=None,
                width=None,
                height=None,
                provenance_id=2,
            ),
            self._observation(
                obs_id=3,
                origin="legacy",
                captured_at=None,
                gps_latitude=47.6062095,
                gps_longitude=-122.3320708,
                camera_make=None,
                camera_model=None,
                width=None,
                height=None,
                provenance_id=None,
                is_legacy_seeded=True,
            ),
        ]

        self.assertEqual(_choose_best_location(observations), (47.60621, -122.332071))

    def test_apply_gps_ref_enforces_expected_sign(self) -> None:
        self.assertEqual(
            _apply_gps_ref(117.611333, "W", positive_refs={"E"}, negative_refs={"W"}),
            -117.611333,
        )
        self.assertEqual(
            _apply_gps_ref(-117.611333, "E", positive_refs={"E"}, negative_refs={"W"}),
            117.611333,
        )
        self.assertEqual(
            _apply_gps_ref(33.622, "N", positive_refs={"N"}, negative_refs={"S"}),
            33.622,
        )


if __name__ == "__main__":
    unittest.main()
