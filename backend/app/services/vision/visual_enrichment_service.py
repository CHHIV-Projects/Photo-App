"""Visual Enrichment candidate preview and run-control service helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.asset_context_label import AssetContextLabel
from app.models.collection import Collection
from app.models.collection_album import CollectionAlbum
from app.models.collection_asset import CollectionAsset
from app.models.place_observation import PlaceObservation
from app.schemas.visual_enrichment import (
    VisualEnrichmentAssetRunSummary,
    VisualEnrichmentCandidateAssetSummary,
    VisualEnrichmentCandidatePreviewRequest,
    VisualEnrichmentCandidatePreviewResponse,
    VisualEnrichmentObjectItem,
    VisualEnrichmentRunRequest,
    VisualEnrichmentRunResponse,
    VisualEnrichmentScoredItem,
)
from app.services.photos.display_url_service import build_asset_display_url_contract
from app.services.vision.google_vision_service import (
    VISION_FEATURE_LANDMARK,
    VISION_FEATURE_LABEL,
    VISION_FEATURE_OBJECT,
    VISION_FEATURE_WEB,
    check_google_vision_runtime,
    detect_with_google_vision,
    detect_with_mock_provider,
    normalize_requested_features,
    persist_landmark_observations_with_ids,
    prepare_vision_derivative,
    write_google_vision_report,
)

GROUPING_TYPE_COLLECTION = "collection"
GROUPING_TYPE_ALBUM = "album"


def _unique_preserve_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _collection_asset_shas(db: Session, *, collection_id: int) -> list[str]:
    collection = db.get(Collection, collection_id)
    if collection is None or collection.grouping_type != GROUPING_TYPE_COLLECTION:
        raise ValueError(f"Collection ID {collection_id} does not exist.")

    direct = [
        row.asset_sha256
        for row in db.execute(
            select(CollectionAsset.asset_sha256).where(CollectionAsset.collection_id == collection_id)
        ).all()
    ]

    album_ids = [
        row.album_id
        for row in db.execute(
            select(CollectionAlbum.album_id)
            .join(Collection, Collection.id == CollectionAlbum.album_id)
            .where(CollectionAlbum.collection_id == collection_id)
            .where(Collection.grouping_type == GROUPING_TYPE_ALBUM)
        ).all()
    ]

    album_assets: list[str] = []
    if album_ids:
        album_assets = [
            row.asset_sha256
            for row in db.execute(
                select(CollectionAsset.asset_sha256)
                .where(CollectionAsset.collection_id.in_(album_ids))
            ).all()
        ]

    return _unique_preserve_order(direct + album_assets)


def _asset_map(db: Session, *, shas: list[str]) -> dict[str, Asset]:
    if not shas:
        return {}
    assets = list(db.scalars(select(Asset).where(Asset.sha256.in_(shas))).all())
    return {row.sha256: row for row in assets}


def preview_visual_enrichment_candidates(
    db: Session,
    *,
    payload: VisualEnrichmentCandidatePreviewRequest,
) -> VisualEnrichmentCandidatePreviewResponse:
    pool_type = (payload.pool_type or "").strip().lower()
    if pool_type != "collection":
        raise ValueError("Only pool_type=collection is supported in this milestone.")

    source_shas = _collection_asset_shas(db, collection_id=payload.pool_id)
    asset_by_sha = _asset_map(db, shas=source_shas)

    visible_assets: list[Asset] = []
    for sha in source_shas:
        asset = asset_by_sha.get(sha)
        if asset is None:
            continue
        if asset.visibility_status != "visible":
            continue
        if payload.canonical_only and asset.duplicate_group_id is not None and not asset.is_canonical:
            continue
        visible_assets.append(asset)

    candidate_assets = visible_assets

    candidate_shas = [item.sha256 for item in candidate_assets]

    observation_sha_set: set[str] = set()
    if candidate_shas:
        observation_rows = db.execute(
            select(PlaceObservation.asset_sha256)
            .where(PlaceObservation.asset_sha256.in_(candidate_shas))
            .where(PlaceObservation.source_type == "google_vision")
            .where(PlaceObservation.observation_type == "landmark")
            .where(PlaceObservation.status.in_(("pending", "accepted", "ignored", "rejected")))
            .distinct()
        ).all()
        observation_sha_set = {row.asset_sha256 for row in observation_rows if row.asset_sha256}

    context_sha_set: set[str] = set()
    if candidate_shas:
        context_rows = db.execute(
            select(AssetContextLabel.asset_sha256)
            .where(AssetContextLabel.asset_sha256.in_(candidate_shas))
            .where(AssetContextLabel.context_type == "landmark")
            .where(AssetContextLabel.status == "active")
            .distinct()
        ).all()
        context_sha_set = {row.asset_sha256 for row in context_rows if row.asset_sha256}

    filtered_assets: list[Asset] = []
    excluded_existing_observations_count = 0
    excluded_existing_context_labels_count = 0

    for asset in candidate_assets:
        has_observation = asset.sha256 in observation_sha_set
        has_context = asset.sha256 in context_sha_set

        if payload.exclude_existing_observations and has_observation:
            excluded_existing_observations_count += 1
            continue
        if payload.exclude_existing_context_labels and has_context:
            excluded_existing_context_labels_count += 1
            continue

        filtered_assets.append(asset)

    run_count = len(filtered_assets)
    limited_assets = filtered_assets[: payload.limit]

    items: list[VisualEnrichmentCandidateAssetSummary] = []
    for asset in limited_assets:
        contract = build_asset_display_url_contract(
            sha256=asset.sha256,
            extension=asset.extension,
            display_preview_path=asset.display_preview_path,
        )
        items.append(
            VisualEnrichmentCandidateAssetSummary(
                asset_sha256=asset.sha256,
                filename=(asset.original_filename or asset.sha256[:12]),
                image_url=contract.image_url,
                display_url=contract.display_url,
                is_canonical=bool(asset.is_canonical),
                duplicate_group_id=asset.duplicate_group_id,
                has_landmark_observation=asset.sha256 in observation_sha_set,
                has_landmark_context_label=asset.sha256 in context_sha_set,
            )
        )

    return VisualEnrichmentCandidatePreviewResponse(
        candidate_count=len(candidate_assets),
        excluded_existing_observations_count=excluded_existing_observations_count,
        excluded_existing_context_labels_count=excluded_existing_context_labels_count,
        run_count=run_count,
        showing_count=len(items),
        assets=items,
    )


def run_visual_enrichment_landmark_detection(
    db: Session,
    *,
    payload: VisualEnrichmentRunRequest,
) -> VisualEnrichmentRunResponse:
    requested_shas = [item.strip().lower() for item in payload.asset_sha256s if item and item.strip()]
    requested_shas = _unique_preserve_order(requested_shas)
    if not requested_shas:
        raise ValueError("At least one asset SHA-256 is required.")

    selected_features: list[str] = []
    if payload.feature_landmark:
        selected_features.append(VISION_FEATURE_LANDMARK)
    if payload.feature_web:
        selected_features.append(VISION_FEATURE_WEB)
    if payload.feature_label:
        selected_features.append(VISION_FEATURE_LABEL)
    if payload.feature_object:
        selected_features.append(VISION_FEATURE_OBJECT)
    if not selected_features:
        raise ValueError("At least one detection feature must be enabled.")

    features = normalize_requested_features(",".join(selected_features))

    live = bool(payload.live)
    runtime = check_google_vision_runtime(live=live)
    if runtime.message is not None and live:
        raise ValueError(runtime.message)

    mock_provider = bool(payload.mock_provider)
    if live:
        mock_provider = False

    asset_by_sha = _asset_map(db, shas=requested_shas)
    missing = [sha for sha in requested_shas if sha not in asset_by_sha]
    if missing:
        raise ValueError(f"Unknown asset SHA-256: {', '.join(missing[:3])}")

    assets = [asset_by_sha[sha] for sha in requested_shas]

    report: dict[str, Any] = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "live" if live else "dry_run",
        "features_requested": list(features),
        "requested_asset_count": len(requested_shas),
        "processed_asset_count": len(assets),
        "results": [],
        "summary": {
            "processed_count": len(assets),
            "provider_calls_attempted": 0,
            "observations_created_count": 0,
            "no_landmark_count": 0,
            "failed_count": 0,
        },
    }
    asset_results: list[VisualEnrichmentAssetRunSummary] = []

    for asset in assets:
        entry: dict[str, Any] = {
            "asset_sha256": asset.sha256,
            "filename": (asset.original_filename or asset.sha256[:12]),
            "status": "pending",
            "error": None,
            "features_requested": list(features),
        }
        derivative_info = None
        try:
            derivative_info = prepare_vision_derivative(asset, keep_derivatives=False)
            entry["derivative"] = {
                "source": derivative_info.source,
                "path": str(derivative_info.path),
                "width": derivative_info.width,
                "height": derivative_info.height,
            }
            with derivative_info.path.open("rb") as handle:
                image_bytes = handle.read()

            if live:
                report["summary"]["provider_calls_attempted"] = int(report["summary"]["provider_calls_attempted"]) + 1
                detection = detect_with_google_vision(image_bytes, features=features)
            elif mock_provider:
                detection = detect_with_mock_provider(asset.sha256, features=features)
            else:
                detection = {
                    "landmarks": [],
                    "web_entities": [],
                    "best_guess_labels": [],
                    "labels": [],
                    "objects": [],
                    "raw": {},
                }

            landmarks = detection["landmarks"]
            web_entities = detection.get("web_entities", [])
            best_guess_labels = detection.get("best_guess_labels", [])
            labels = detection.get("labels", [])
            objects = detection.get("objects", [])

            created_observation_ids: list[int] = []
            if VISION_FEATURE_LANDMARK in features and landmarks:
                created_observation_ids = persist_landmark_observations_with_ids(
                    db,
                    asset_sha256=asset.sha256,
                    landmarks=landmarks,
                )
                report["summary"]["observations_created_count"] = (
                    int(report["summary"]["observations_created_count"]) + len(created_observation_ids)
                )
            elif VISION_FEATURE_LANDMARK in features:
                report["summary"]["no_landmark_count"] = int(report["summary"]["no_landmark_count"]) + 1

            db.commit()
            entry["status"] = "ok"
            entry["landmarks_found"] = len(landmarks)
            entry["web_entities_found"] = len(web_entities)
            entry["best_guess_labels"] = list(best_guess_labels)
            entry["labels_found"] = len(labels)
            entry["objects_found"] = len(objects)
            entry["created_observation_ids"] = created_observation_ids
            entry["no_landmark"] = bool(VISION_FEATURE_LANDMARK in features and not landmarks)
            entry["landmarks"] = [item.raw_payload for item in landmarks]
            entry["web_entities"] = [item.raw_payload for item in web_entities]
            entry["labels"] = [item.raw_payload for item in labels]
            entry["objects"] = [item.raw_payload for item in objects]
            entry["raw"] = detection.get("raw", {})

            asset_results.append(
                VisualEnrichmentAssetRunSummary(
                    asset_sha256=asset.sha256,
                    filename=(asset.original_filename or asset.sha256[:12]),
                    status="ok",
                    landmarks=[
                        VisualEnrichmentScoredItem(description=item.name, score=item.confidence)
                        for item in landmarks[:3]
                    ],
                    web_entities=[
                        VisualEnrichmentScoredItem(description=item.description, score=item.confidence)
                        for item in web_entities[:3]
                    ],
                    best_guess_labels=list(best_guess_labels[:3]),
                    labels=[
                        VisualEnrichmentScoredItem(description=item.name, score=item.confidence)
                        for item in labels[:3]
                    ],
                    objects=[
                        VisualEnrichmentObjectItem(name=item.name, score=item.confidence)
                        for item in objects[:3]
                    ],
                    created_observations=len(created_observation_ids),
                    no_landmark=bool(VISION_FEATURE_LANDMARK in features and not landmarks),
                )
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            report["summary"]["failed_count"] = int(report["summary"]["failed_count"]) + 1
            entry["status"] = "failed"
            entry["error"] = str(exc)
            entry["no_landmark"] = False
            asset_results.append(
                VisualEnrichmentAssetRunSummary(
                    asset_sha256=asset.sha256,
                    filename=(asset.original_filename or asset.sha256[:12]),
                    status="failed",
                    error=str(exc),
                    created_observations=0,
                    no_landmark=False,
                )
            )
        finally:
            if derivative_info is not None and derivative_info.temporary and derivative_info.path.exists():
                try:
                    derivative_info.path.unlink(missing_ok=True)
                except OSError:
                    pass

        report["results"].append(entry)

    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    report_path = write_google_vision_report(report)

    return VisualEnrichmentRunResponse(
        requested_count=len(requested_shas),
        processed_count=int(report["summary"]["processed_count"]),
        provider_calls_attempted=int(report["summary"]["provider_calls_attempted"]),
        observations_created_count=int(report["summary"]["observations_created_count"]),
        no_landmark_count=int(report["summary"]["no_landmark_count"]),
        failed_count=int(report["summary"]["failed_count"]),
        report_path=str(Path(report_path)),
        mode=("live" if live else "dry_run"),
        features_requested=list(features),
        asset_results=asset_results,
    )
