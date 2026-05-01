"""JPEG preview generation for assets.

Converts non-browser-renderable formats (e.g. HEIC) to JPEG derivatives.
Originals in the vault are never modified.

Preview layout: storage/previews/{sha256[:2]}/{sha256}.jpg
Served at:      /media/previews/{sha256[:2]}/{sha256}.jpg
"""

from __future__ import annotations

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
