"""Generate missing review face crops without rerunning detection or clustering."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import cv2
from sqlalchemy import select

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
WORKSPACE_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.face import Face

USAGE = "Usage: python scripts/generate_missing_face_crops.py [--dry-run]"

REVIEW_ROOT = (WORKSPACE_ROOT / "storage" / "review").resolve()
UNASSIGNED_FOLDER = "unassigned"
FACE_FILENAME_PATTERN = re.compile(r"^face_(\d+)__", re.IGNORECASE)


def _parse_args(argv: list[str]) -> bool:
    dry_run = False

    for arg in argv[1:]:
        if arg == "--dry-run":
            dry_run = True
            continue
        raise ValueError(f"Unknown argument: {arg}")

    return dry_run


def _sanitize_filename(name: str, max_len: int = 80) -> str:
    sanitized = re.sub(r"[<>:\"/\\|?*\x00-\x1F]", "_", name)
    sanitized = re.sub(r"\s+", "_", sanitized).strip("._ ")
    if not sanitized:
        sanitized = "unknown_filename"
    return sanitized[:max_len]


def _clamp_crop(
    x: int, y: int, width: int, height: int, image_width: int, image_height: int
) -> tuple[int, int, int, int] | None:
    left = max(0, x)
    top = max(0, y)
    right = min(image_width, x + width)
    bottom = min(image_height, y + height)

    if right <= left or bottom <= top:
        return None

    return left, top, right, bottom


def _existing_face_ids(review_root: Path) -> set[int]:
    existing: set[int] = set()
    if not review_root.exists():
        return existing

    for candidate in review_root.rglob("*"):
        if not candidate.is_file():
            continue
        match = FACE_FILENAME_PATTERN.match(candidate.name)
        if not match:
            continue
        existing.add(int(match.group(1)))

    return existing


def _resolve_output_path(face: Face, asset: Asset, review_root: Path) -> Path:
    folder_name = f"cluster_{face.cluster_id}" if face.cluster_id is not None else UNASSIGNED_FOLDER
    output_dir = review_root / folder_name

    original_stem = Path(asset.original_filename).stem or asset.original_filename
    name_part = _sanitize_filename(original_stem)
    file_name = f"face_{face.id}__asset_{face.asset_sha256[:12]}__{name_part}.jpg"
    return output_dir / file_name


def main() -> int:
    try:
        dry_run = _parse_args(sys.argv)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 1

    existing = _existing_face_ids(REVIEW_ROOT)

    summary = {
        "total_faces": 0,
        "existing_crops": 0,
        "generated": 0,
        "missing_source": 0,
        "invalid_bbox": 0,
        "image_load_failed": 0,
        "write_failures": 0,
        "missing_asset_record": 0,
    }

    db = SessionLocal()
    try:
        face_asset_rows = db.execute(
            select(Face, Asset)
            .outerjoin(Asset, Asset.sha256 == Face.asset_sha256)
            .order_by(Face.id.asc())
        ).all()

        summary["total_faces"] = len(face_asset_rows)

        print(f"Scan started. dry_run={dry_run}")

        for face, asset in face_asset_rows:
            print(f"Processing face {face.id}...")

            if face.id in existing:
                summary["existing_crops"] += 1
                print("  Crop exists -> skipping")
                continue

            if asset is None:
                summary["missing_asset_record"] += 1
                print("  Warning: asset record missing -> skipping")
                continue

            source_image_path = Path(asset.vault_path)
            if not source_image_path.exists():
                summary["missing_source"] += 1
                print(f"  Warning: source image missing -> {source_image_path}")
                continue

            image = cv2.imread(str(source_image_path))
            if image is None:
                summary["image_load_failed"] += 1
                print("  Warning: failed to load source image -> skipping")
                continue

            image_height, image_width = image.shape[:2]
            clamped = _clamp_crop(
                face.bbox_x,
                face.bbox_y,
                face.bbox_width,
                face.bbox_height,
                image_width,
                image_height,
            )
            if clamped is None:
                summary["invalid_bbox"] += 1
                print("  Warning: invalid bounding box after clamp -> skipping")
                continue

            left, top, right, bottom = clamped
            crop = image[top:bottom, left:right]
            if crop.size == 0:
                summary["invalid_bbox"] += 1
                print("  Warning: empty crop after slicing -> skipping")
                continue

            output_path = _resolve_output_path(face, asset, REVIEW_ROOT)

            if dry_run:
                summary["generated"] += 1
                print(f"  Would generate crop -> {output_path}")
                existing.add(face.id)
                continue

            output_path.parent.mkdir(parents=True, exist_ok=True)
            write_ok = cv2.imwrite(str(output_path), crop)
            if not write_ok:
                summary["write_failures"] += 1
                print(f"  Warning: failed to write crop -> {output_path}")
                continue

            summary["generated"] += 1
            existing.add(face.id)
            print(f"  Generated crop -> saved to {output_path}")
    except Exception as exc:  # noqa: BLE001
        print(f"Fatal script error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print("\nSummary")
    print(f"  Total faces: {summary['total_faces']}")
    print(f"  Existing crops: {summary['existing_crops']}")
    print(f"  Generated: {summary['generated']}")
    print(f"  Missing source images: {summary['missing_source']}")
    print(f"  Missing asset records: {summary['missing_asset_record']}")
    print(f"  Invalid/empty bbox crops: {summary['invalid_bbox']}")
    print(f"  Image load failures: {summary['image_load_failed']}")
    print(f"  Write failures: {summary['write_failures']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
