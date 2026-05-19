"""Unit tests for centralized display preview URL contract behavior."""

from __future__ import annotations

import unittest

from app.services.photos.display_url_service import (
    DISPLAY_SOURCE_MISSING_PREVIEW,
    DISPLAY_SOURCE_ORIGINAL,
    DISPLAY_SOURCE_PREVIEW,
    DISPLAY_SOURCE_VIDEO_PLACEHOLDER,
    build_asset_display_url_contract,
)


class DisplayUrlServiceTests(unittest.TestCase):
    def test_heic_with_preview_uses_preview_display_url(self) -> None:
        contract = build_asset_display_url_contract(
            sha256="a" * 64,
            extension=".heic",
            display_preview_path="/media/previews/aa/" + ("a" * 64) + ".jpg",
        )
        self.assertEqual(contract.display_source, DISPLAY_SOURCE_PREVIEW)
        self.assertTrue(contract.has_display_preview)
        self.assertEqual(contract.display_url, contract.image_url)
        self.assertIsNotNone(contract.display_url)

    def test_heic_without_preview_returns_null_display_url(self) -> None:
        contract = build_asset_display_url_contract(
            sha256="b" * 64,
            extension=".heic",
            display_preview_path=None,
        )
        self.assertEqual(contract.display_source, DISPLAY_SOURCE_MISSING_PREVIEW)
        self.assertFalse(contract.has_display_preview)
        self.assertIsNone(contract.display_url)
        self.assertIsNone(contract.image_url)
        self.assertTrue(contract.original_url.endswith(".heic"))

    def test_tiff_with_preview_uses_preview_display_url(self) -> None:
        contract = build_asset_display_url_contract(
            sha256="c" * 64,
            extension=".tiff",
            display_preview_path="/media/previews/cc/" + ("c" * 64) + ".jpg",
        )
        self.assertEqual(contract.display_source, DISPLAY_SOURCE_PREVIEW)
        self.assertEqual(contract.display_url, contract.image_url)
        self.assertIsNotNone(contract.display_url)

    def test_browser_safe_jpg_without_preview_uses_original_display_url(self) -> None:
        contract = build_asset_display_url_contract(
            sha256="d" * 64,
            extension=".jpg",
            display_preview_path=None,
        )
        self.assertEqual(contract.display_source, DISPLAY_SOURCE_ORIGINAL)
        self.assertEqual(contract.display_url, contract.original_url)
        self.assertEqual(contract.image_url, contract.original_url)

    def test_mov_without_thumbnail_returns_video_placeholder_state(self) -> None:
        contract = build_asset_display_url_contract(
            sha256="e" * 64,
            extension=".mov",
            display_preview_path=None,
        )
        self.assertEqual(contract.display_source, DISPLAY_SOURCE_VIDEO_PLACEHOLDER)
        self.assertIsNone(contract.display_url)
        self.assertIsNone(contract.image_url)
        self.assertTrue(contract.original_url.endswith(".mov"))


if __name__ == "__main__":
    unittest.main()
