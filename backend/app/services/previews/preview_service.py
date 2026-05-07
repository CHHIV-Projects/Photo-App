"""JPEG preview generation and eligibility inspection for assets.

Converts non-browser-renderable formats (e.g. HEIC, TIFF) or known
extension/content mismatch cases to JPEG derivatives. Originals in the vault are
never modified.

Preview layout: storage/previews/{sha256[:2]}/{sha256}.jpg
Served at:      /media/previews/{sha256[:2]}/{sha256}.jpg
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pillow_heif
from PIL import Image

# Register pillow-heif opener so Pillow can open .heic / .heif files.
# Safe to call multiple times — registration is idempotent.
pillow_heif.register_heif_opener()

_BACKEND_ROOT = Path(__file__).resolve().parents[4]
_PREVIEWS_ROOT: Path = _BACKEND_ROOT / "storage" / "previews"

# Longest-side cap for generated previews (keeps file size reasonable).
_MAX_PREVIEW_LONGEST_SIDE = 2048

_HEIC_EXTENSIONS = frozenset({".heic", ".heif"})
_TIFF_EXTENSIONS = frozenset({".tif", ".tiff"})
_MISMATCH_SNIFF_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png"})


@dataclass(frozen=True)
class PreviewEligibility:
    requires_preview: bool
    preview_kind: str | None = None
    actual_format: str | None = None


def _normalize_extension(extension: str | None) -> str:
    if not extension:
        return ""
    normalized = extension.strip().lower()
    return normalized if normalized.startswith(".") else f".{normalized}"


def inspect_preview_eligibility(vault_path: str | Path, extension: str | None) -> PreviewEligibility:
    """Determine whether an asset should receive a browser-safe preview.

    Rules for 12.29:
    - HEIC/HEIF by extension always require preview.
    - TIFF/TIF by extension always require preview.
    - JPG/JPEG/PNG only require preview when Pillow reports TIFF content.
    """
    normalized_extension = _normalize_extension(extension)

    if normalized_extension in _HEIC_EXTENSIONS:
        return PreviewEligibility(requires_preview=True, preview_kind="heic")
    if normalized_extension in _TIFF_EXTENSIONS:
        return PreviewEligibility(requires_preview=True, preview_kind="tiff")
    if normalized_extension not in _MISMATCH_SNIFF_EXTENSIONS:
        return PreviewEligibility(requires_preview=False)

    with Image.open(Path(vault_path)) as img:
        actual_format = (img.format or "").upper() or None

    if actual_format == "TIFF":
        return PreviewEligibility(
            requires_preview=True,
            preview_kind="mismatch",
            actual_format=actual_format,
        )

    return PreviewEligibility(requires_preview=False, actual_format=actual_format)


def build_preview_path(sha256: str) -> Path:
    """Return the filesystem path where a preview for *sha256* would be stored."""
    return _PREVIEWS_ROOT / sha256[:2] / f"{sha256}.jpg"


def build_preview_url(sha256: str) -> str:
    """Return the browser-accessible URL for a preview."""
    return f"/media/previews/{sha256[:2]}/{sha256}.jpg"


def generate_preview(vault_path: str | Path, sha256: str) -> Path:
    """Generate a JPEG preview for the given asset.

    - Skips silently if the preview file already exists.
    - Never modifies *vault_path*.
    - Downsizes to at most ``_MAX_PREVIEW_LONGEST_SIDE`` on the longest side.

    Returns the preview ``Path`` (whether newly created or already present).
    """
    preview_path = build_preview_path(sha256)
    if preview_path.exists():
        return preview_path

    source = Path(vault_path)
    with Image.open(source) as img:
        # For multi-page TIFF, generate from the first page only in 12.29.
        if getattr(img, "n_frames", 1) > 1:
            img.seek(0)
        img = img.convert("RGB")

        w, h = img.size
        longest = max(w, h)
        if longest > _MAX_PREVIEW_LONGEST_SIDE:
            scale = _MAX_PREVIEW_LONGEST_SIDE / longest
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            img = img.resize((new_w, new_h), Image.LANCZOS)

        preview_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(preview_path), "JPEG", quality=85, optimize=True)

    return preview_path
