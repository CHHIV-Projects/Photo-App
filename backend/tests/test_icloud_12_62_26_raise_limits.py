"""Tests for Milestone 12.62.26: Raise candidate scan and acquire limits for recent sync."""

from __future__ import annotations

import base64
import hashlib
import json
import unittest

from pydantic import ValidationError

from app.schemas.admin import InternalIcloudRunRequest
from app.services.icloud_acquisition.exact_selection_adapter import (
    ExactSelectionLogicalItem,
    ExactSelectionResource,
)
from app.services.icloud_acquisition.exact_selection_protocol import (
    MAX_CANDIDATE_SCAN_LIMIT,
    MAX_HELPER_JSON_BYTES,
    MAX_SELECTED_ITEM_COUNT,
)


class IcloudLimitsRaisedTest(unittest.TestCase):
    """Verify that candidate scan and acquire limits are raised to 1000 for recent sync."""

    def test_protocol_max_candidate_scan_limit_is_1000(self) -> None:
        """Confirm MAX_CANDIDATE_SCAN_LIMIT constant is 1000."""
        self.assertEqual(MAX_CANDIDATE_SCAN_LIMIT, 1000)

    def test_protocol_max_selected_item_count_is_1000(self) -> None:
        """Confirm MAX_SELECTED_ITEM_COUNT constant is 1000."""
        self.assertEqual(MAX_SELECTED_ITEM_COUNT, 1000)

    def test_schema_candidate_search_cap_default_is_1000(self) -> None:
        """Verify InternalIcloudRunRequest default candidate_search_cap is 1000."""
        req = InternalIcloudRunRequest(source_id=1)
        self.assertEqual(req.candidate_search_cap, 1000)

    def test_schema_candidate_search_cap_max_is_1000(self) -> None:
        """Verify InternalIcloudRunRequest accepts candidate_search_cap up to 1000."""
        req = InternalIcloudRunRequest(source_id=1, candidate_search_cap=1000)
        self.assertEqual(req.candidate_search_cap, 1000)

    def test_schema_candidate_search_cap_rejects_above_1000(self) -> None:
        """Verify InternalIcloudRunRequest rejects candidate_search_cap above 1000."""
        with self.assertRaises(ValidationError):
            InternalIcloudRunRequest(source_id=1, candidate_search_cap=1001)

    def test_schema_total_limit_default_is_500(self) -> None:
        """Verify InternalIcloudRunRequest default total_limit is 500."""
        req = InternalIcloudRunRequest(source_id=1)
        self.assertEqual(req.total_limit, 500)

    def test_schema_total_limit_max_is_1000(self) -> None:
        """Verify InternalIcloudRunRequest accepts total_limit up to 1000."""
        req = InternalIcloudRunRequest(source_id=1, total_limit=1000)
        self.assertEqual(req.total_limit, 1000)

    def test_schema_total_limit_rejects_above_1000(self) -> None:
        """Verify InternalIcloudRunRequest rejects total_limit above 1000."""
        with self.assertRaises(ValidationError):
            InternalIcloudRunRequest(source_id=1, total_limit=1001)

    def test_schema_accepts_recent_sync_defaults(self) -> None:
        """Verify schema accepts the recent sync defaults: candidate_search_cap=1000, total_limit=500."""
        req = InternalIcloudRunRequest(
            source_id=1,
            candidate_search_cap=1000,
            total_limit=500,
            media_scope="all_supported_media",
        )
        self.assertEqual(req.candidate_search_cap, 1000)
        self.assertEqual(req.total_limit, 500)
        self.assertEqual(req.media_scope, "all_supported_media")

    def test_schema_accepts_admin_override_max_limits(self) -> None:
        """Verify schema accepts admin override of total_limit to 1000."""
        req = InternalIcloudRunRequest(
            source_id=1,
            candidate_search_cap=1000,
            total_limit=1000,
            media_scope="all_supported_media",
        )
        self.assertEqual(req.total_limit, 1000)


class HelperJsonPayloadSizeTest(unittest.TestCase):
    """Verify that a 1000-item worst-case payload remains under MAX_HELPER_JSON_BYTES."""

    def _checksum(self, content: bytes) -> str:
        """Generate iCloud-compatible checksum (0x01 marker + SHA1)."""
        return base64.b64encode(b"\x01" + hashlib.sha1(content).digest()).decode("ascii")

    def _make_realistic_payload_1000_items(self) -> str:
        """Construct a representative 1000-item selected payload JSON.

        Each item includes:
        - item_id
        - grouping
        - identity_ambiguous
        - resources (1 ordinary still or 2 for Live Photo pair)

        Each resource includes:
        - resource_id, role, relative_path, expected_size, expected_checksum, content_type
        """
        items = []
        sample_content = b"x" * 100_000  # ~100 KB content per item

        for i in range(1000):
            year = 2026
            month = 1 + (i % 12)
            day = 1 + (i % 28)
            base_name = f"IMG_{5000 + i}"

            if i % 3 == 0:
                # Ordinary still
                item = {
                    "item_id": f"asset_{i:05d}",
                    "grouping": "primary_asset_explicit",
                    "identity_ambiguous": False,
                    "resources": [
                        {
                            "resource_id": "primary_original",
                            "role": "primary_original",
                            "relative_path": f"{year}/{month:02d}/{day:02d}/{base_name}.HEIC",
                            "expected_size": len(sample_content),
                            "expected_checksum": self._checksum(sample_content),
                            "content_type": "image/heic",
                        }
                    ],
                }
            elif i % 3 == 1:
                # Video
                item = {
                    "item_id": f"asset_{i:05d}",
                    "grouping": "primary_asset_explicit",
                    "identity_ambiguous": False,
                    "resources": [
                        {
                            "resource_id": "primary_original",
                            "role": "primary_original",
                            "relative_path": f"{year}/{month:02d}/{day:02d}/{base_name}.MOV",
                            "expected_size": len(sample_content),
                            "expected_checksum": self._checksum(sample_content),
                            "content_type": "video/quicktime",
                        }
                    ],
                }
            else:
                # Live Photo pair (HEIC + MOV)
                item = {
                    "item_id": f"asset_{i:05d}",
                    "grouping": "primary_asset_explicit",
                    "identity_ambiguous": False,
                    "resources": [
                        {
                            "resource_id": "primary_original",
                            "role": "primary_original",
                            "relative_path": f"{year}/{month:02d}/{day:02d}/{base_name}.HEIC",
                            "expected_size": len(sample_content),
                            "expected_checksum": self._checksum(sample_content),
                            "content_type": "image/heic",
                        },
                        {
                            "resource_id": "live_photo_original",
                            "role": "live_photo_original",
                            "relative_path": f"{year}/{month:02d}/{day:02d}/{base_name}_HEVC.MOV",
                            "expected_size": len(sample_content),
                            "expected_checksum": self._checksum(sample_content),
                            "content_type": "video/quicktime",
                        },
                    ],
                }

            items.append(item)

        # Build the exact-selection download payload shape
        payload = {
            "operation": "download_selected",
            "items": items,
        }

        return json.dumps(payload)

    def test_1000_item_payload_fits_in_max_helper_bytes(self) -> None:
        """Verify worst-case 1000-item payload is under MAX_HELPER_JSON_BYTES."""
        payload_json = self._make_realistic_payload_1000_items()
        payload_bytes = payload_json.encode("utf-8")
        payload_size = len(payload_bytes)

        self.assertLess(
            payload_size,
            MAX_HELPER_JSON_BYTES,
            f"1000-item payload ({payload_size} bytes) exceeds MAX_HELPER_JSON_BYTES ({MAX_HELPER_JSON_BYTES} bytes). "
            f"Need to raise MAX_HELPER_JSON_BYTES or optimize payload structure.",
        )

        # Report payload size for reference
        mb = payload_size / (1024 * 1024)
        print(f"1000-item worst-case payload: {payload_size} bytes ({mb:.2f} MB), max allowed: {MAX_HELPER_JSON_BYTES} bytes")


class AllSupportedMediaRegressionTest(unittest.TestCase):
    """Verify that all_supported_media still works with raised limits."""

    def test_schema_accepts_all_supported_media_at_raised_limits(self) -> None:
        """Confirm all_supported_media media scope is accepted at 1000/500 limits."""
        req = InternalIcloudRunRequest(
            source_id=1,
            candidate_search_cap=1000,
            total_limit=500,
            media_scope="all_supported_media",
        )
        self.assertEqual(req.media_scope, "all_supported_media")
        self.assertEqual(req.candidate_search_cap, 1000)
        self.assertEqual(req.total_limit, 500)

    def test_schema_accepts_ordinary_stills_at_raised_limits(self) -> None:
        """Confirm ordinary_stills media scope is accepted at 1000/500 limits."""
        req = InternalIcloudRunRequest(
            source_id=1,
            candidate_search_cap=1000,
            total_limit=500,
            media_scope="ordinary_stills",
        )
        self.assertEqual(req.media_scope, "ordinary_stills")

    def test_schema_all_supported_media_accepts_max_total_limit(self) -> None:
        """Confirm all_supported_media works with total_limit=1000 (admin override)."""
        req = InternalIcloudRunRequest(
            source_id=1,
            candidate_search_cap=1000,
            total_limit=1000,
            media_scope="all_supported_media",
        )
        self.assertEqual(req.total_limit, 1000)


if __name__ == "__main__":
    unittest.main()
