"""Unit tests for deterministic metadata canonicalization selectors."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from app.models.asset_metadata_observation import AssetMetadataObservation
from app.services.metadata.canonicalization_service import (
    _choose_best_camera_value,
    _choose_best_captured_at,
    _choose_best_dimensions,
)


class MetadataCanonicalizationServiceTests(unittest.TestCase):
    def _observation(
        self,
        *,
        obs_id: int,
        origin: str,
        captured_at: datetime | None,
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
                camera_make=None,
                camera_model=None,
                width=6000,
                height=4000,
                provenance_id=2,
                extension=".heic",
            ),
        ]

        self.assertEqual(_choose_best_dimensions(observations), (6000, 4000))


if __name__ == "__main__":
    unittest.main()
