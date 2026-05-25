"""Run a controlled Google Vision test harness for selected assets.

Examples:
  # Dry-run by default (no external API call)
  python backend/scripts/run_google_vision_test.py --asset-sha256 <sha>

  # Live landmark-only run
  python backend/scripts/run_google_vision_test.py --asset-sha256 <sha> --live --features landmark

  # Live run with landmark + label + object
  python backend/scripts/run_google_vision_test.py \
    --asset-sha256 <sha1> --asset-sha256 <sha2> \
    --live --features landmark,label,object --limit 2

  # Dry-run with mock provider candidates persisted for landmark path checks
  python backend/scripts/run_google_vision_test.py --asset-sha256 <sha> --mock-provider
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.places.place_schema import ensure_place_schema
from app.services.vision.google_vision_service import (
    check_google_vision_runtime,
    detect_with_google_vision,
    detect_with_mock_provider,
    load_selected_assets,
    normalize_requested_features,
    persist_landmark_observations,
    prepare_vision_derivative,
    write_google_vision_report,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Google Vision test harness for selected assets.")
    parser.add_argument(
        "--asset-sha256",
        action="append",
        required=True,
        help="Asset SHA-256 to process (repeatable).",
    )
    parser.add_argument(
        "--features",
        default="landmark",
        help="Comma-separated features: landmark,label,object (default: landmark).",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Enable live Google Vision calls. Without this flag, run is dry-run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Explicitly request dry-run mode (already the default).",
    )
    parser.add_argument(
        "--mock-provider",
        action="store_true",
        help="In dry-run mode, generate mock provider candidates for local persistence testing.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional run cap in addition to VISION_MAX_IMAGES_PER_RUN.",
    )
    parser.add_argument(
        "--keep-derivatives",
        action="store_true",
        help="Keep generated derivative files for debugging.",
    )
    return parser


def _effective_limit(cli_limit: int | None) -> int:
    config_limit = max(1, int(settings.vision_max_images_per_run))
    if cli_limit is None:
        return config_limit
    return max(1, min(int(cli_limit), config_limit))


def main() -> int:
    args = _build_parser().parse_args()
    live = bool(args.live)

    runtime = check_google_vision_runtime(live=live)
    if runtime.message is not None and live:
        print(f"[config] {runtime.message}")
        print(
            "[hint] Use dry-run (default) or configure VISION_ENABLED with "
            "GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_CLOUD_VISION_API_KEY for --live."
        )
        return 1

    requested_features = normalize_requested_features(args.features)
    limit = _effective_limit(args.limit)

    db = SessionLocal()
    try:
        ensure_place_schema(db)

        selected_assets, missing_assets = load_selected_assets(db, args.asset_sha256)
        assets_to_process = selected_assets[:limit]

        report: dict[str, object] = {
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "mode": "live" if live else "dry_run",
            "vision_enabled": settings.vision_enabled,
            "features_requested": list(requested_features),
            "selected_asset_count": len(args.asset_sha256),
            "resolved_asset_count": len(selected_assets),
            "processed_asset_count": len(assets_to_process),
            "missing_assets": missing_assets,
            "limits": {
                "vision_max_images_per_run": settings.vision_max_images_per_run,
                "effective_limit": limit,
            },
            "derivative": {
                "preferred_source": "existing_preview_then_generated",
                "long_edge_target": 1280,
                "keep_derivatives": bool(args.keep_derivatives),
            },
            "results": [],
            "summary": {
                "successful_assets": 0,
                "failed_assets": 0,
                "landmarks_found": 0,
                "labels_found": 0,
                "objects_found": 0,
                "landmark_observations_created": 0,
                "provider_calls_attempted": 0,
            },
        }

        if not assets_to_process:
            report_path = write_google_vision_report(report)
            print(json.dumps({"status": "no_assets", "report_path": str(report_path)}, indent=2))
            return 1 if missing_assets else 0

        for asset in assets_to_process:
            entry: dict[str, object] = {
                "asset_sha256": asset.sha256,
                "status": "pending",
                "error": None,
            }
            derivative_info = None
            try:
                derivative_info = prepare_vision_derivative(asset, keep_derivatives=bool(args.keep_derivatives))
                entry["derivative"] = {
                    "source": derivative_info.source,
                    "path": str(derivative_info.path),
                    "temporary": derivative_info.temporary,
                    "width": derivative_info.width,
                    "height": derivative_info.height,
                }

                with derivative_info.path.open("rb") as handle:
                    image_bytes = handle.read()

                if live:
                    report["summary"]["provider_calls_attempted"] = int(report["summary"]["provider_calls_attempted"]) + 1
                    detection = detect_with_google_vision(image_bytes, features=requested_features)
                elif args.mock_provider:
                    detection = detect_with_mock_provider(asset.sha256, features=requested_features)
                else:
                    detection = {"landmarks": [], "labels": [], "objects": [], "raw": {}}

                landmarks = detection["landmarks"]
                labels = detection["labels"]
                objects = detection["objects"]

                observations_created = 0
                if landmarks:
                    observations_created = persist_landmark_observations(
                        db,
                        asset_sha256=asset.sha256,
                        landmarks=landmarks,
                    )
                db.commit()

                report["summary"]["successful_assets"] = int(report["summary"]["successful_assets"]) + 1
                report["summary"]["landmarks_found"] = int(report["summary"]["landmarks_found"]) + len(landmarks)
                report["summary"]["labels_found"] = int(report["summary"]["labels_found"]) + len(labels)
                report["summary"]["objects_found"] = int(report["summary"]["objects_found"]) + len(objects)
                report["summary"]["landmark_observations_created"] = int(
                    report["summary"]["landmark_observations_created"]
                ) + observations_created

                entry["status"] = "ok"
                entry["landmarks"] = [
                    {
                        "name": item.name,
                        "confidence": item.confidence,
                        "latitude": item.latitude,
                        "longitude": item.longitude,
                    }
                    for item in landmarks
                ]
                entry["labels"] = [
                    {
                        "name": item.name,
                        "confidence": item.confidence,
                    }
                    for item in labels
                ]
                entry["objects"] = [
                    {
                        "name": item.name,
                        "confidence": item.confidence,
                        "bounding_poly": item.bounding_poly,
                    }
                    for item in objects
                ]
                entry["raw_provider_result"] = detection["raw"]
                entry["landmark_observations_created"] = observations_created
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                report["summary"]["failed_assets"] = int(report["summary"]["failed_assets"]) + 1
                entry["status"] = "failed"
                entry["error"] = str(exc)
            finally:
                if derivative_info is not None and derivative_info.temporary and derivative_info.path.exists():
                    try:
                        derivative_info.path.unlink(missing_ok=True)
                    except OSError:
                        pass

            report["results"].append(entry)

        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        report_path = write_google_vision_report(report)

        output = {
            "status": "ok" if int(report["summary"]["failed_assets"]) == 0 else "partial_failure",
            "mode": report["mode"],
            "features_requested": report["features_requested"],
            "processed_asset_count": report["processed_asset_count"],
            "summary": report["summary"],
            "report_path": str(report_path),
        }
        print(json.dumps(output, indent=2))

        return 0 if int(report["summary"]["failed_assets"]) == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
