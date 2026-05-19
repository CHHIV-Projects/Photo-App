"""Centralized display/original URL contract for asset media rendering."""

from __future__ import annotations

from dataclasses import dataclass

BROWSER_SAFE_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
}

NON_BROWSER_SAFE_IMAGE_EXTENSIONS = {
    ".heic",
    ".heif",
    ".tif",
    ".tiff",
}

VIDEO_EXTENSIONS = {
    ".mov",
    ".mp4",
    ".m4v",
    ".avi",
    ".mkv",
    ".3gp",
}

DISPLAY_SOURCE_PREVIEW = "preview"
DISPLAY_SOURCE_ORIGINAL = "original"
DISPLAY_SOURCE_MISSING_PREVIEW = "missing_preview"
DISPLAY_SOURCE_VIDEO_PLACEHOLDER = "video_placeholder"
DISPLAY_SOURCE_UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class AssetDisplayUrlContract:
    """Normalized URL contract for visual asset rendering in UI surfaces."""

    display_url: str | None
    original_url: str
    has_display_preview: bool
    display_source: str
    image_url: str | None


def _normalize_extension(extension: str) -> str:
    ext = (extension or "").strip().lower()
    if not ext:
        return ""
    if ext.startswith("."):
        return ext
    return f".{ext}"


def build_original_asset_url(sha256: str, extension: str) -> str:
    ext = _normalize_extension(extension)
    prefix = sha256[:2]
    filename = f"{sha256}{ext}"
    return f"/media/assets/{prefix}/{filename}"


def build_asset_display_url_contract(
    *,
    sha256: str,
    extension: str,
    display_preview_path: str | None,
) -> AssetDisplayUrlContract:
    """Return a centralized display/original URL contract for one asset.

    Rules:
    - If display preview exists, use preview URL for display.
    - Else if original is browser-safe image, use original URL for display.
    - Else return null display_url with explicit display_source metadata.
    """

    original_url = build_original_asset_url(sha256, extension)
    ext = _normalize_extension(extension)

    if display_preview_path:
        return AssetDisplayUrlContract(
            display_url=display_preview_path,
            original_url=original_url,
            has_display_preview=True,
            display_source=DISPLAY_SOURCE_PREVIEW,
            image_url=display_preview_path,
        )

    if ext in BROWSER_SAFE_IMAGE_EXTENSIONS:
        return AssetDisplayUrlContract(
            display_url=original_url,
            original_url=original_url,
            has_display_preview=False,
            display_source=DISPLAY_SOURCE_ORIGINAL,
            image_url=original_url,
        )

    if ext in NON_BROWSER_SAFE_IMAGE_EXTENSIONS:
        return AssetDisplayUrlContract(
            display_url=None,
            original_url=original_url,
            has_display_preview=False,
            display_source=DISPLAY_SOURCE_MISSING_PREVIEW,
            image_url=None,
        )

    if ext in VIDEO_EXTENSIONS:
        return AssetDisplayUrlContract(
            display_url=None,
            original_url=original_url,
            has_display_preview=False,
            display_source=DISPLAY_SOURCE_VIDEO_PLACEHOLDER,
            image_url=None,
        )

    return AssetDisplayUrlContract(
        display_url=None,
        original_url=original_url,
        has_display_preview=False,
        display_source=DISPLAY_SOURCE_UNSUPPORTED,
        image_url=None,
    )
