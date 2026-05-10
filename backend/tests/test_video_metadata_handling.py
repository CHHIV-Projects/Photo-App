"""Unit tests for video-aware metadata extraction and normalization."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.asset import Asset
from app.services.metadata.canonicalization_service import _extract_observation_from_metadata
from app.services.metadata.exif_extractor import _extract_single_metadata
from app.services.metadata.metadata_normalizer import normalize_asset_metadata


class VideoMetadataHandlingTests(unittest.TestCase):
    def test_mov_extraction_uses_quicktime_creation_date(self) -> None:
        asset = Asset(
            sha256="sha-mov",
            vault_path="C:/vault/video.mov",
            original_filename="video.mov",
            original_source_path="C:/source/video.mov",
            extension=".mov",
            size_bytes=123,
            modified_timestamp_utc=datetime(2026, 5, 8, 19, 21, 6, tzinfo=timezone.utc),
        )
        metadata = {
            "QuickTime:CreationDate": "2026:05:08 12:21:06-07:00",
            "QuickTime:CreateDate": "2026:05:08 19:21:06",
            "QuickTime:Make": "Apple",
            "QuickTime:Model": "iPhone 14 Plus",
        }

        extracted = _extract_single_metadata(metadata, asset)

        self.assertIsNotNone(extracted)
        assert extracted is not None
        self.assertEqual(extracted.exif_datetime_original, datetime(2026, 5, 8, 19, 21, 6))
        self.assertEqual(extracted.exif_create_date, datetime(2026, 5, 8, 19, 21, 6))
        self.assertEqual(extracted.camera_make, "Apple")
        self.assertEqual(extracted.camera_model, "iPhone 14 Plus")

    def test_video_normalization_marks_container_date_as_high_trust(self) -> None:
        asset = Asset(
            sha256="sha-mov",
            vault_path="C:/vault/video.mov",
            original_filename="video.mov",
            original_source_path="C:/source/video.mov",
            extension=".mov",
            size_bytes=123,
            modified_timestamp_utc=datetime(2026, 5, 8, 19, 21, 6, tzinfo=timezone.utc),
            exif_datetime_original=datetime(2026, 5, 8, 19, 21, 6),
            camera_make="Apple",
            camera_model="iPhone 14 Plus",
        )

        normalized = normalize_asset_metadata(asset)

        self.assertEqual(normalized.capture_type, "digital")
        self.assertEqual(normalized.capture_time_trust, "high")
        self.assertFalse(normalized.is_scan)
        self.assertFalse(normalized.needs_date_estimation)
        self.assertEqual(normalized.source_type, "iphone")
        self.assertEqual(normalized.captured_at, datetime(2026, 5, 8, 19, 21, 6, tzinfo=timezone.utc))

    def test_video_normalization_uses_filesystem_fallback_as_low_trust(self) -> None:
        asset = Asset(
            sha256="sha-mp4",
            vault_path="C:/vault/video.mp4",
            original_filename="video.mp4",
            original_source_path="C:/source/video.mp4",
            extension=".mp4",
            size_bytes=123,
            modified_timestamp_utc=datetime(2012, 8, 9, 0, 18, 17, tzinfo=timezone.utc),
        )

        normalized = normalize_asset_metadata(asset)

        self.assertEqual(normalized.capture_type, "digital")
        self.assertEqual(normalized.capture_time_trust, "low")
        self.assertFalse(normalized.is_scan)
        self.assertFalse(normalized.needs_date_estimation)
        self.assertEqual(normalized.captured_at, datetime(2012, 8, 9, 0, 18, 17, tzinfo=timezone.utc))

    def test_video_observation_extraction_uses_quicktime_fields(self) -> None:
        metadata = {
            "QuickTime:CreationDate": "2026:05:08 12:21:06-07:00",
            "QuickTime:CreateDate": "2026:05:08 19:21:06",
            "QuickTime:Make": "Apple",
            "QuickTime:Model": "iPhone 14 Plus",
            "QuickTime:ImageWidth": 1920,
            "QuickTime:ImageHeight": 1440,
        }

        observed = _extract_observation_from_metadata(Path("C:/vault/video.mov"), metadata)

        self.assertIsNotNone(observed)
        assert observed is not None
        self.assertEqual(observed.captured_at_observed, datetime(2026, 5, 8, 19, 21, 6, tzinfo=timezone.utc))
        self.assertEqual(observed.camera_make, "Apple")
        self.assertEqual(observed.camera_model, "iPhone 14 Plus")
        self.assertEqual((observed.width, observed.height), (1920, 1440))


if __name__ == "__main__":
    unittest.main()
