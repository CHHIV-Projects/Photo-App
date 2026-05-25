"""Google Vision test harness utilities for selected assets.

12.60 scope:
- Controlled selected-asset execution only.
- Dry-run by default (no external calls).
- Landmark candidates may persist as pending place observations.
- Label/Object candidates are report-only.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import httpx
import pillow_heif
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.asset import Asset
from app.services.places.observation_service import CreatePlaceObservationInput, create_place_observation

try:
    from google.cloud import vision  # type: ignore
except Exception:  # pragma: no cover - handled at runtime
    vision = None


pillow_heif.register_heif_opener()

BACKEND_ROOT = Path(__file__).resolve().parents[4]
REPORT_DIR = BACKEND_ROOT / "storage" / "logs" / "google_vision_reports"
DERIVATIVE_DEBUG_DIR = BACKEND_ROOT / "storage" / "logs" / "google_vision_derivatives"

MEDIA_PREVIEW_PREFIX = "/media/previews/"

VISION_FEATURE_LANDMARK = "landmark"
VISION_FEATURE_LABEL = "label"
VISION_FEATURE_OBJECT = "object"
SUPPORTED_FEATURES = (VISION_FEATURE_LANDMARK, VISION_FEATURE_LABEL, VISION_FEATURE_OBJECT)

DEFAULT_DERIVATIVE_LONG_EDGE = 1280
MIN_REUSE_PREVIEW_LONG_EDGE = 1024
MAX_DERIVATIVE_LONG_EDGE = 1600
_VISION_ANNOTATE_URL = "https://vision.googleapis.com/v1/images:annotate"


@dataclass(frozen=True)
class GoogleVisionRuntimeCheck:
    enabled: bool
    live_mode: bool
    dry_run: bool
    message: str | None


@dataclass(frozen=True)
class DerivativeInfo:
    path: Path
    source: str
    temporary: bool
    width: int
    height: int


@dataclass(frozen=True)
class LandmarkCandidate:
    name: str
    confidence: float | None
    latitude: float | None
    longitude: float | None
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class LabelCandidate:
    name: str
    confidence: float | None
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class ObjectCandidate:
    name: str
    confidence: float | None
    bounding_poly: list[dict[str, float | None]]
    raw_payload: dict[str, Any]


def normalize_requested_features(raw_features: str | None) -> tuple[str, ...]:
    if raw_features is None or not raw_features.strip():
        return (VISION_FEATURE_LANDMARK,)

    tokens: list[str] = []
    for token in raw_features.split(","):
        normalized = token.strip().lower()
        if not normalized:
            continue
        if normalized not in SUPPORTED_FEATURES:
            raise ValueError(f"Unsupported feature: {normalized}")
        if normalized not in tokens:
            tokens.append(normalized)

    if not tokens:
        return (VISION_FEATURE_LANDMARK,)
    return tuple(tokens)


def check_google_vision_runtime(*, live: bool) -> GoogleVisionRuntimeCheck:
    if not live:
        return GoogleVisionRuntimeCheck(enabled=settings.vision_enabled, live_mode=False, dry_run=True, message=None)

    if not settings.vision_enabled:
        return GoogleVisionRuntimeCheck(
            enabled=False,
            live_mode=True,
            dry_run=False,
            message="VISION_ENABLED is false. Set VISION_ENABLED=true to allow live Google Vision calls.",
        )

    has_service_account = bool(settings.google_application_credentials)
    has_api_key = bool(settings.google_cloud_vision_api_key)
    if not has_service_account and not has_api_key:
        return GoogleVisionRuntimeCheck(
            enabled=True,
            live_mode=True,
            dry_run=False,
            message=(
                "Neither GOOGLE_APPLICATION_CREDENTIALS nor GOOGLE_CLOUD_VISION_API_KEY is configured. "
                "Configure credentials before using --live."
            ),
        )

    if vision is None and not has_api_key:
        return GoogleVisionRuntimeCheck(
            enabled=True,
            live_mode=True,
            dry_run=False,
            message="google-cloud-vision is not available and API key auth is not configured.",
        )

    return GoogleVisionRuntimeCheck(enabled=True, live_mode=True, dry_run=False, message=None)


def _feature_type_for_rest(feature: str) -> str:
    if feature == VISION_FEATURE_LANDMARK:
        return "LANDMARK_DETECTION"
    if feature == VISION_FEATURE_LABEL:
        return "LABEL_DETECTION"
    if feature == VISION_FEATURE_OBJECT:
        return "OBJECT_LOCALIZATION"
    raise ValueError(f"Unsupported feature: {feature}")


def _parse_landmarks_from_rest(payload: dict[str, Any]) -> list[LandmarkCandidate]:
    items: list[LandmarkCandidate] = []
    for row in payload.get("landmarkAnnotations", []) or []:
        locations_payload: list[dict[str, float | None]] = []
        latitude: float | None = None
        longitude: float | None = None
        for loc in row.get("locations", []) or []:
            lat_lng = loc.get("latLng", {}) or {}
            lat_value = lat_lng.get("latitude")
            lon_value = lat_lng.get("longitude")
            locations_payload.append(
                {
                    "latitude": float(lat_value) if lat_value is not None else None,
                    "longitude": float(lon_value) if lon_value is not None else None,
                }
            )
            if latitude is None and longitude is None and lat_value is not None and lon_value is not None:
                latitude = float(lat_value)
                longitude = float(lon_value)

        vertices: list[dict[str, float | None]] = []
        for vertex in (row.get("boundingPoly", {}) or {}).get("vertices", []) or []:
            vertices.append(
                {
                    "x": float(vertex.get("x", 0.0)) if vertex.get("x") is not None else None,
                    "y": float(vertex.get("y", 0.0)) if vertex.get("y") is not None else None,
                }
            )

        raw_payload = {
            "provider": "google_vision",
            "feature": "LANDMARK_DETECTION",
            "description": row.get("description"),
            "score": row.get("score"),
            "topicality": row.get("topicality"),
            "locations": locations_payload,
            "bounding_poly": vertices,
            "mid": row.get("mid"),
            "mock_provider": False,
        }
        items.append(
            LandmarkCandidate(
                name=str(row.get("description") or "").strip(),
                confidence=float(row.get("score")) if row.get("score") is not None else None,
                latitude=latitude,
                longitude=longitude,
                raw_payload=raw_payload,
            )
        )
    return [item for item in items if item.name]


def _parse_labels_from_rest(payload: dict[str, Any]) -> list[LabelCandidate]:
    items: list[LabelCandidate] = []
    for row in payload.get("labelAnnotations", []) or []:
        name = str(row.get("description") or "").strip()
        if not name:
            continue
        items.append(
            LabelCandidate(
                name=name,
                confidence=float(row.get("score")) if row.get("score") is not None else None,
                raw_payload={
                    "provider": "google_vision",
                    "feature": "LABEL_DETECTION",
                    "description": row.get("description"),
                    "score": row.get("score"),
                    "topicality": row.get("topicality"),
                    "mid": row.get("mid"),
                    "mock_provider": False,
                },
            )
        )
    return items


def _parse_objects_from_rest(payload: dict[str, Any]) -> list[ObjectCandidate]:
    items: list[ObjectCandidate] = []
    for row in payload.get("localizedObjectAnnotations", []) or []:
        vertices: list[dict[str, float | None]] = []
        for vertex in (row.get("boundingPoly", {}) or {}).get("normalizedVertices", []) or []:
            vertices.append(
                {
                    "x": float(vertex.get("x")) if vertex.get("x") is not None else None,
                    "y": float(vertex.get("y")) if vertex.get("y") is not None else None,
                }
            )

        name = str(row.get("name") or "").strip()
        if not name:
            continue

        items.append(
            ObjectCandidate(
                name=name,
                confidence=float(row.get("score")) if row.get("score") is not None else None,
                bounding_poly=vertices,
                raw_payload={
                    "provider": "google_vision",
                    "feature": "OBJECT_LOCALIZATION",
                    "name": row.get("name"),
                    "score": row.get("score"),
                    "bounding_poly": vertices,
                    "mid": row.get("mid"),
                    "mock_provider": False,
                },
            )
        )
    return items


def _detect_with_google_vision_api_key(image_bytes: bytes, *, features: tuple[str, ...]) -> dict[str, Any]:
    if not settings.google_cloud_vision_api_key:
        raise RuntimeError("GOOGLE_CLOUD_VISION_API_KEY is not configured.")

    encoded = base64.b64encode(image_bytes).decode("ascii")
    request_payload = {
        "requests": [
            {
                "image": {"content": encoded},
                "features": [{"type": _feature_type_for_rest(feature)} for feature in features],
            }
        ]
    }

    response = httpx.post(
        _VISION_ANNOTATE_URL,
        params={"key": settings.google_cloud_vision_api_key},
        json=request_payload,
        timeout=30.0,
    )
    response.raise_for_status()

    payload = response.json()
    responses = payload.get("responses", []) or []
    if not responses:
        raise RuntimeError("Google Vision returned no responses.")
    first = responses[0]

    error_obj = first.get("error")
    if error_obj:
        message = (error_obj.get("message") or "Google Vision API error").strip()
        raise RuntimeError(message)

    landmarks = _parse_landmarks_from_rest(first)
    labels = _parse_labels_from_rest(first)
    objects = _parse_objects_from_rest(first)

    raw: dict[str, Any] = {}
    if VISION_FEATURE_LANDMARK in features:
        raw[VISION_FEATURE_LANDMARK] = [item.raw_payload for item in landmarks]
    if VISION_FEATURE_LABEL in features:
        raw[VISION_FEATURE_LABEL] = [item.raw_payload for item in labels]
    if VISION_FEATURE_OBJECT in features:
        raw[VISION_FEATURE_OBJECT] = [item.raw_payload for item in objects]

    return {
        "landmarks": landmarks,
        "labels": labels,
        "objects": objects,
        "raw": raw,
    }


def load_selected_assets(db: Session, asset_sha256_list: list[str]) -> tuple[list[Asset], list[str]]:
    ordered_unique_sha: list[str] = []
    seen: set[str] = set()
    for raw_sha in asset_sha256_list:
        normalized = (raw_sha or "").strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered_unique_sha.append(normalized)

    if not ordered_unique_sha:
        return [], []

    rows = list(db.scalars(select(Asset).where(Asset.sha256.in_(ordered_unique_sha))).all())
    asset_by_sha = {row.sha256.lower(): row for row in rows}

    selected_assets: list[Asset] = []
    missing: list[str] = []
    for sha in ordered_unique_sha:
        asset = asset_by_sha.get(sha)
        if asset is None:
            missing.append(sha)
        else:
            selected_assets.append(asset)

    return selected_assets, missing


def _preview_url_to_path(display_preview_path: str) -> Path | None:
    normalized = display_preview_path.strip()
    if not normalized:
        return None
    if normalized.startswith(MEDIA_PREVIEW_PREFIX):
        relative_part = normalized[len(MEDIA_PREVIEW_PREFIX) :].lstrip("/")
        return (BACKEND_ROOT / "storage" / "previews" / relative_part).resolve()

    direct_path = Path(normalized)
    if direct_path.is_absolute():
        return direct_path
    return (BACKEND_ROOT / direct_path).resolve()


def _resolve_asset_source_path(asset: Asset) -> Path:
    configured_vault_root = Path(settings.vault_path).resolve()
    raw = Path(asset.vault_path)

    if raw.is_absolute() and raw.exists():
        return raw.resolve()

    backend_relative = (BACKEND_ROOT / raw).resolve()
    if backend_relative.exists():
        return backend_relative

    vault_relative = (configured_vault_root / raw).resolve()
    if vault_relative.exists():
        return vault_relative

    raise FileNotFoundError(f"Asset source file does not exist for {asset.sha256}")


def _image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        width, height = image.size
    return width, height


def _build_temp_derivative_path(asset_sha256: str, *, keep_derivatives: bool) -> Path:
    if keep_derivatives:
        DERIVATIVE_DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return DERIVATIVE_DEBUG_DIR / f"{timestamp}_{asset_sha256}.jpg"

    tmp_file = NamedTemporaryFile(prefix=f"vision_{asset_sha256[:12]}_", suffix=".jpg", delete=False)
    tmp_path = Path(tmp_file.name)
    tmp_file.close()
    return tmp_path


def prepare_vision_derivative(
    asset: Asset,
    *,
    keep_derivatives: bool,
    long_edge: int = DEFAULT_DERIVATIVE_LONG_EDGE,
) -> DerivativeInfo:
    clamped_long_edge = max(MIN_REUSE_PREVIEW_LONG_EDGE, min(int(long_edge), MAX_DERIVATIVE_LONG_EDGE))

    if asset.display_preview_path:
        preview_path = _preview_url_to_path(asset.display_preview_path)
        if preview_path is not None and preview_path.exists():
            width, height = _image_size(preview_path)
            if max(width, height) >= MIN_REUSE_PREVIEW_LONG_EDGE:
                return DerivativeInfo(
                    path=preview_path,
                    source="existing_preview",
                    temporary=False,
                    width=width,
                    height=height,
                )

    source_path = _resolve_asset_source_path(asset)
    derivative_path = _build_temp_derivative_path(asset.sha256, keep_derivatives=keep_derivatives)

    with Image.open(source_path) as image:
        if getattr(image, "n_frames", 1) > 1:
            image.seek(0)
        rgb = image.convert("RGB")
        width, height = rgb.size
        longest = max(width, height)
        if longest > clamped_long_edge:
            ratio = clamped_long_edge / float(longest)
            new_size = (max(1, int(width * ratio)), max(1, int(height * ratio)))
            rgb = rgb.resize(new_size, Image.LANCZOS)
            width, height = rgb.size

        derivative_path.parent.mkdir(parents=True, exist_ok=True)
        rgb.save(str(derivative_path), "JPEG", quality=85, optimize=True)

    return DerivativeInfo(
        path=derivative_path,
        source="generated_derivative",
        temporary=not keep_derivatives,
        width=width,
        height=height,
    )


def _parse_landmarks(annotation: Any, *, mock_provider: bool = False) -> list[LandmarkCandidate]:
    items: list[LandmarkCandidate] = []
    for row in annotation.landmark_annotations:
        latitude = None
        longitude = None
        locations_payload: list[dict[str, float | None]] = []
        for loc in row.locations:
            lat_lng = getattr(loc, "lat_lng", None)
            lat_value = float(getattr(lat_lng, "latitude", 0.0)) if lat_lng is not None else None
            lon_value = float(getattr(lat_lng, "longitude", 0.0)) if lat_lng is not None else None
            locations_payload.append({"latitude": lat_value, "longitude": lon_value})
            if latitude is None and longitude is None and lat_value is not None and lon_value is not None:
                latitude = lat_value
                longitude = lon_value

        vertices: list[dict[str, float | None]] = []
        polygon = getattr(row, "bounding_poly", None)
        if polygon is not None:
            for vertex in polygon.vertices:
                vertices.append({"x": float(getattr(vertex, "x", 0.0)), "y": float(getattr(vertex, "y", 0.0))})

        raw_payload = {
            "provider": "google_vision",
            "feature": "LANDMARK_DETECTION",
            "description": row.description,
            "score": float(getattr(row, "score", 0.0)),
            "topicality": float(getattr(row, "topicality", 0.0)) if getattr(row, "topicality", None) is not None else None,
            "locations": locations_payload,
            "bounding_poly": vertices,
            "mock_provider": mock_provider,
        }
        items.append(
            LandmarkCandidate(
                name=row.description,
                confidence=float(getattr(row, "score", 0.0)) if getattr(row, "score", None) is not None else None,
                latitude=latitude,
                longitude=longitude,
                raw_payload=raw_payload,
            )
        )

    return items


def _parse_labels(annotation: Any, *, mock_provider: bool = False) -> list[LabelCandidate]:
    items: list[LabelCandidate] = []
    for row in annotation.label_annotations:
        items.append(
            LabelCandidate(
                name=row.description,
                confidence=float(getattr(row, "score", 0.0)) if getattr(row, "score", None) is not None else None,
                raw_payload={
                    "provider": "google_vision",
                    "feature": "LABEL_DETECTION",
                    "description": row.description,
                    "score": float(getattr(row, "score", 0.0)),
                    "topicality": float(getattr(row, "topicality", 0.0)) if getattr(row, "topicality", None) is not None else None,
                    "mock_provider": mock_provider,
                },
            )
        )
    return items


def _parse_objects(annotation: Any, *, mock_provider: bool = False) -> list[ObjectCandidate]:
    items: list[ObjectCandidate] = []
    for row in annotation.localized_object_annotations:
        vertices: list[dict[str, float | None]] = []
        polygon = getattr(row, "bounding_poly", None)
        if polygon is not None:
            for vertex in polygon.normalized_vertices:
                vertices.append({"x": float(getattr(vertex, "x", 0.0)), "y": float(getattr(vertex, "y", 0.0))})

        items.append(
            ObjectCandidate(
                name=row.name,
                confidence=float(getattr(row, "score", 0.0)) if getattr(row, "score", None) is not None else None,
                bounding_poly=vertices,
                raw_payload={
                    "provider": "google_vision",
                    "feature": "OBJECT_LOCALIZATION",
                    "name": row.name,
                    "score": float(getattr(row, "score", 0.0)),
                    "bounding_poly": vertices,
                    "mid": getattr(row, "mid", None),
                    "mock_provider": mock_provider,
                },
            )
        )
    return items


def detect_with_google_vision(
    image_bytes: bytes,
    *,
    features: tuple[str, ...],
) -> dict[str, Any]:
    if settings.google_application_credentials and vision is not None:
        pass
    elif settings.google_cloud_vision_api_key:
        return _detect_with_google_vision_api_key(image_bytes, features=features)

    if vision is None:
        raise RuntimeError("google-cloud-vision is not installed and API key fallback is unavailable.")

    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)

    raw: dict[str, Any] = {}
    landmarks: list[LandmarkCandidate] = []
    labels: list[LabelCandidate] = []
    objects: list[ObjectCandidate] = []

    if VISION_FEATURE_LANDMARK in features:
        response = client.landmark_detection(image=image)
        if response.error.message:
            raise RuntimeError(f"Landmark detection failed: {response.error.message}")
        landmarks = _parse_landmarks(response)
        raw[VISION_FEATURE_LANDMARK] = [item.raw_payload for item in landmarks]

    if VISION_FEATURE_LABEL in features:
        response = client.label_detection(image=image)
        if response.error.message:
            raise RuntimeError(f"Label detection failed: {response.error.message}")
        labels = _parse_labels(response)
        raw[VISION_FEATURE_LABEL] = [item.raw_payload for item in labels]

    if VISION_FEATURE_OBJECT in features:
        response = client.object_localization(image=image)
        if response.error.message:
            raise RuntimeError(f"Object localization failed: {response.error.message}")
        objects = _parse_objects(response)
        raw[VISION_FEATURE_OBJECT] = [item.raw_payload for item in objects]

    return {
        "landmarks": landmarks,
        "labels": labels,
        "objects": objects,
        "raw": raw,
    }


def detect_with_mock_provider(asset_sha256: str, *, features: tuple[str, ...]) -> dict[str, Any]:
    class _MockLandmark:
        def __init__(self, description: str) -> None:
            self.description = description
            self.score = 0.99
            self.topicality = 0.99
            self.locations = []
            self.bounding_poly = type("MockBoundingPoly", (), {"vertices": []})()

    class _MockLabel:
        def __init__(self, description: str) -> None:
            self.description = description
            self.score = 0.9
            self.topicality = 0.9

    class _MockObject:
        def __init__(self, name: str) -> None:
            self.name = name
            self.score = 0.85
            self.mid = None
            self.bounding_poly = type("MockObjPoly", (), {"normalized_vertices": []})()

    landmarks: list[LandmarkCandidate] = []
    labels: list[LabelCandidate] = []
    objects: list[ObjectCandidate] = []

    if VISION_FEATURE_LANDMARK in features:
        landmarks = _parse_landmarks(type("MockResponse", (), {"landmark_annotations": [_MockLandmark(f"Mock Landmark {asset_sha256[:8]}")]})(), mock_provider=True)
    if VISION_FEATURE_LABEL in features:
        labels = _parse_labels(type("MockResponse", (), {"label_annotations": [_MockLabel("mock-label")]})(), mock_provider=True)
    if VISION_FEATURE_OBJECT in features:
        objects = _parse_objects(type("MockResponse", (), {"localized_object_annotations": [_MockObject("mock-object")]})(), mock_provider=True)

    return {
        "landmarks": landmarks,
        "labels": labels,
        "objects": objects,
        "raw": {
            VISION_FEATURE_LANDMARK: [item.raw_payload for item in landmarks],
            VISION_FEATURE_LABEL: [item.raw_payload for item in labels],
            VISION_FEATURE_OBJECT: [item.raw_payload for item in objects],
        },
    }


def persist_landmark_observations(
    db: Session,
    *,
    asset_sha256: str,
    landmarks: list[LandmarkCandidate],
) -> int:
    created = 0
    for candidate in landmarks:
        create_place_observation(
            db,
            CreatePlaceObservationInput(
                asset_sha256=asset_sha256,
                place_id=None,
                source_type="google_vision",
                observation_type="landmark",
                status="pending",
                raw_label=candidate.name,
                latitude=candidate.latitude,
                longitude=candidate.longitude,
                confidence=candidate.confidence,
                raw_response_json=candidate.raw_payload,
            ),
            commit=False,
        )
        created += 1
    return created


def write_google_vision_report(report: dict[str, Any]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = REPORT_DIR / f"google_vision_test_{timestamp}.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    return path
