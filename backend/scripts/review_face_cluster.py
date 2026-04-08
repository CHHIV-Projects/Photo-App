"""Export cropped face images for manual review of one or more clusters."""

from __future__ import annotations

import json
import re
import shutil
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
from app.models.face_cluster import FaceCluster

USAGE = (
    "Usage: python scripts/review_face_cluster.py [--no-prompt] "
    "[--output-root <folder>] <cluster_id> [cluster_id ...]"
)


def _parse_args(argv: list[str]) -> tuple[list[int], Path | None, bool]:
    args = argv[1:]
    no_prompt = False
    output_root: Path | None = None
    filtered: list[str] = []

    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--no-prompt":
            no_prompt = True
            idx += 1
            continue
        if arg == "--output-root":
            if idx + 1 >= len(args):
                raise ValueError("--output-root requires a folder path.")
            raw_output_root = args[idx + 1]
            output_root = Path(raw_output_root).expanduser()
            if not output_root.is_absolute():
                output_root = (WORKSPACE_ROOT / output_root).resolve()
            idx += 2
            continue

        filtered.append(arg)
        idx += 1

    if not filtered:
        if no_prompt:
            raise ValueError("At least one cluster_id is required when --no-prompt is set.")
        try:
            raw_cluster_ids = input(
                "Enter one or more cluster IDs to review (space or comma separated): "
            ).replace(",", " ").split()
        except (EOFError, KeyboardInterrupt) as exc:
            raise ValueError("Cancelled.") from exc
        filtered = raw_cluster_ids

    cluster_ids: list[int] = []
    if len(filtered) == 2 and output_root is None:
        # Legacy single-cluster usage: <cluster_id> <output_folder>
        try:
            cluster_id = int(filtered[0])
            if cluster_id <= 0:
                raise ValueError("cluster_id must be a positive integer.")
            cluster_ids = [cluster_id]
            output_root = Path(filtered[1]).expanduser()
            if not output_root.is_absolute():
                output_root = (WORKSPACE_ROOT / output_root).resolve()
            return cluster_ids, output_root, True
        except ValueError:
            # Fall through and interpret all values as cluster IDs.
            cluster_ids = []

    for raw_cluster_id in filtered:
        try:
            cluster_id = int(raw_cluster_id)
        except ValueError as exc:
            raise ValueError(f"cluster_id must be an integer. Got: {raw_cluster_id}") from exc

        if cluster_id <= 0:
            raise ValueError("cluster_id must be a positive integer.")

        cluster_ids.append(cluster_id)

    if not cluster_ids:
        raise ValueError("At least one valid cluster_id is required.")

    return cluster_ids, output_root, False


def _resolve_output_dir(
    cluster_id: int,
    output_root: Path | None,
    legacy_single_output_dir: bool,
) -> Path:
    if output_root is None:
        return (WORKSPACE_ROOT / "storage" / "review" / f"cluster_{cluster_id}").resolve()

    if legacy_single_output_dir:
        return output_root

    return (output_root / f"cluster_{cluster_id}").resolve()


def _review_cluster(db, cluster_id: int, output_dir: Path) -> dict:
    cluster = db.get(FaceCluster, cluster_id)
    if cluster is None:
        raise ValueError(f"cluster_id={cluster_id} does not exist.")

    face_asset_rows = db.execute(
        select(Face, Asset)
        .join(Asset, Asset.sha256 == Face.asset_sha256)
        .where(Face.cluster_id == cluster_id)
        .order_by(Face.id.asc())
    ).all()

    if not face_asset_rows:
        raise ValueError(f"cluster_id={cluster_id} exists but has 0 faces to review.")

    _prepare_output_folder(output_dir)

    saved_crops: list[dict] = []
    failures: list[dict] = []

    for face, asset in face_asset_rows:
        base_record = _serialize_face(face, asset)
        image_path = Path(asset.vault_path)

        if not image_path.exists():
            failures.append(
                {
                    **base_record,
                    "reason": "source_image_missing",
                }
            )
            continue

        image = cv2.imread(str(image_path))
        if image is None:
            failures.append(
                {
                    **base_record,
                    "reason": "image_load_failed",
                }
            )
            continue

        h, w = image.shape[:2]
        clamped = _clamp_crop(face.bbox_x, face.bbox_y, face.bbox_width, face.bbox_height, w, h)
        if clamped is None:
            failures.append(
                {
                    **base_record,
                    "reason": "invalid_crop_after_clamp",
                }
            )
            continue

        left, top, right, bottom = clamped
        crop = image[top:bottom, left:right]
        if crop.size == 0:
            failures.append(
                {
                    **base_record,
                    "reason": "empty_crop",
                }
            )
            continue

        original_stem = Path(asset.original_filename).stem or asset.original_filename
        name_part = _sanitize_filename(original_stem)
        output_name = f"face_{face.id}__asset_{face.asset_sha256[:12]}__{name_part}.jpg"
        output_path = output_dir / output_name

        write_ok = cv2.imwrite(str(output_path), crop)
        if not write_ok:
            failures.append(
                {
                    **base_record,
                    "reason": "crop_write_failed",
                    "output_path": str(output_path),
                }
            )
            continue

        saved_crops.append(
            {
                **base_record,
                "crop_path": str(output_path),
                "clamped_bbox": {
                    "left": left,
                    "top": top,
                    "right": right,
                    "bottom": bottom,
                },
            }
        )

    manifest = {
        "cluster_id": cluster_id,
        "output_dir": str(output_dir),
        "total_faces_found": len(face_asset_rows),
        "crops_saved": len(saved_crops),
        "failures": failures,
        "faces": saved_crops,
    }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return {
        "cluster_id": cluster_id,
        "output_dir": str(output_dir),
        "manifest_path": str(manifest_path),
        "total_faces_found": len(face_asset_rows),
        "crops_saved": len(saved_crops),
        "failures": len(failures),
        "failure_examples": failures[:5],
    }


def _sanitize_filename(name: str, max_len: int = 80) -> str:
    # Keep readable names while removing Windows-invalid characters.
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


def _serialize_face(face: Face, asset: Asset) -> dict:
    return {
        "face_id": face.id,
        "cluster_id": face.cluster_id,
        "asset_sha256": face.asset_sha256,
        "vault_path": asset.vault_path,
        "original_filename": asset.original_filename,
        "original_source_path": asset.original_source_path,
        "bbox_x": face.bbox_x,
        "bbox_y": face.bbox_y,
        "bbox_width": face.bbox_width,
        "bbox_height": face.bbox_height,
        "confidence_score": face.confidence_score,
    }


def _prepare_output_folder(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for child in output_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=False)
        else:
            child.unlink()


def main() -> int:
    try:
        cluster_ids, output_root, legacy_single_output_dir = _parse_args(sys.argv)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        summaries: list[dict] = []
        errors: list[dict] = []

        for cluster_id in cluster_ids:
            output_dir = _resolve_output_dir(cluster_id, output_root, legacy_single_output_dir)
            try:
                summaries.append(_review_cluster(db, cluster_id, output_dir))
            except ValueError as exc:
                errors.append({"cluster_id": cluster_id, "error": str(exc)})
    finally:
        db.close()

    if len(cluster_ids) == 1 and errors:
        print(f"Error: {errors[0]['error']}", file=sys.stderr)
        return 1

    if len(cluster_ids) == 1:
        print(json.dumps(summaries[0], indent=2))
        return 0

    output = {
        "requested_cluster_ids": cluster_ids,
        "clusters_processed": len(summaries),
        "clusters_failed": len(errors),
        "cluster_summaries": summaries,
        "errors": errors,
    }
    print(json.dumps(output, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
