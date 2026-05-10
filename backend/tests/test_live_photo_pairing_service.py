"""Unit tests for Live Photo pairing normalization and reporting fields."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.live_photo.pairing_reporting import build_report_payload
from app.services.live_photo.pairing_schema import LivePhotoPairingSchemaSummary
from app.services.live_photo.pairing_service import LivePhotoPairingResult, _normalize_motion_basename


class LivePhotoPairingNormalizationTests(unittest.TestCase):
    def test_motion_suffix_hevc_is_stripped_case_insensitive(self) -> None:
        key, variant, suffix = _normalize_motion_basename("img_5637_hevc")
        self.assertEqual(key, "img_5637")
        self.assertEqual(variant, "motion_suffix_hevc")
        self.assertEqual(suffix, "_hevc")

    def test_motion_without_approved_suffix_keeps_simple_basename(self) -> None:
        key, variant, suffix = _normalize_motion_basename("img_5637")
        self.assertEqual(key, "img_5637")
        self.assertEqual(variant, "simple_basename")
        self.assertIsNone(suffix)

    def test_motion_non_trailing_hevc_is_not_stripped(self) -> None:
        key, variant, suffix = _normalize_motion_basename("img_hevc_5637")
        self.assertEqual(key, "img_hevc_5637")
        self.assertEqual(variant, "simple_basename")
        self.assertIsNone(suffix)


class LivePhotoPairingReportingTests(unittest.TestCase):
    def test_report_includes_suffix_visibility_fields(self) -> None:
        result = LivePhotoPairingResult(
            scanned_rows=10,
            candidate_groups=5,
            inserted=2,
            updated=1,
            unchanged=3,
            removed_stale=0,
            skipped_missing_source=0,
            skipped_ambiguous=1,
            skipped_suspicious_delta=0,
            pairs_created_simple_basename=1,
            pairs_created_motion_suffix=1,
            motion_suffixes_seen={"_hevc": 2},
            generated_at_utc="2026-05-09T00:00:00Z",
            sample_pairs=[],
        )
        payload = build_report_payload(LivePhotoPairingSchemaSummary(ensured_tables=[]), result)

        summary = payload["summary"]
        assert isinstance(summary, dict)
        self.assertEqual(summary["pairs_created_simple_basename"], 1)
        self.assertEqual(summary["pairs_created_motion_suffix"], 1)
        self.assertEqual(summary["motion_suffixes_seen"], {"_hevc": 2})
        self.assertEqual(summary["ambiguous_skipped"], 1)


if __name__ == "__main__":
    unittest.main()
