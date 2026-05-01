"""Content tagger: load EfficientNet-B0 via timm, infer top-k labels, persist to DB."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pillow_heif
from PIL import Image

# Register pillow-heif so PIL.Image.open() can handle .heic / .heif files.
pillow_heif.register_heif_opener()
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.asset_content_tag import AssetContentTag
from app.services.content.tag_vocabulary import get_tag_type, map_label

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model loading (lazy singleton to avoid repeated disk I/O)
# ---------------------------------------------------------------------------

_model = None
_transforms = None
_class_descriptions = None


def ensure_content_tag_runtime_available() -> None:
    """Fail fast if required ML runtime dependencies are missing."""
    try:
        import timm  # noqa: F401
        import torch  # noqa: F401
        import torchvision  # noqa: F401
    except ModuleNotFoundError as exc:
        missing_name = exc.name or "required dependency"
        raise RuntimeError(
            "Content tagging requires timm, torch, and torchvision. "
            f"Missing dependency: {missing_name}. "
            "Install backend requirements and rerun the script."
        ) from exc


def _get_model_and_transforms() -> tuple[Any, Any]:
    """Return (model, transforms) — loaded once, then cached globally."""
    global _model, _transforms, _class_descriptions
    if _model is not None:
        return _model, _transforms

    ensure_content_tag_runtime_available()

    import timm
    from timm.data import ImageNetInfo, infer_imagenet_subset

    model = timm.create_model("efficientnet_b0", pretrained=True)
    model.eval()

    data_config = timm.data.resolve_model_data_config(model)
    transforms = timm.data.create_transform(**data_config, is_training=False)
    subset = infer_imagenet_subset(model.pretrained_cfg) or "imagenet-1k"
    imagenet_info = ImageNetInfo(subset)

    _model = model
    _transforms = transforms
    _class_descriptions = imagenet_info.label_descriptions()
    return model, transforms


# ---------------------------------------------------------------------------
# Per-asset inference
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TaggingResult:
    asset_sha256: str
    tags: list[tuple[str, float]]   # [(label, confidence_score), ...]


@dataclass
class BatchTaggingOutcome:
    tagged: list[TaggingResult] = field(default_factory=list)
    skipped_already_tagged: list[str] = field(default_factory=list)
    failures: list[tuple[str, str]] = field(default_factory=list)  # (sha256, reason)


def _infer_tags(
    image_path: Path,
    *,
    min_confidence: float,
    max_per_asset: int,
    top_k: int = 10,
) -> list[tuple[str, float]]:
    """Run EfficientNet inference on one image; return whitelisted (label, score) pairs."""
    import torch

    global _class_descriptions

    model, transforms = _get_model_and_transforms()

    img = Image.open(image_path).convert("RGB")
    tensor = transforms(img).unsqueeze(0)  # type: ignore[arg-type]

    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=-1)[0]
        top_probs, top_indices = torch.topk(probs, k=top_k)

    tags: list[tuple[str, float]] = []
    seen_labels: set[str] = set()

    for prob_tensor, idx_tensor in zip(top_probs.tolist(), top_indices.tolist()):
        score = float(prob_tensor)
        if score < min_confidence:
            break
        class_index = int(idx_tensor)
        raw_class = (
            _class_descriptions[class_index]
            if _class_descriptions and class_index < len(_class_descriptions)
            else str(class_index)
        )
        label = map_label(raw_class)
        if label is None or label in seen_labels:
            continue
        seen_labels.add(label)
        tags.append((label, round(score, 4)))
        if len(tags) >= max_per_asset:
            break

    return tags


# ---------------------------------------------------------------------------
# Incremental asset loading
# ---------------------------------------------------------------------------

def load_assets_for_content_tagging(db: Session) -> list[Asset]:
    """Return canonical assets that have not yet been content-tagged.

    An asset is considered tagged if at least one AssetContentTag row exists
    for it.  This approach avoids adding a column to the assets table.
    """
    tagged_subq = (
        select(AssetContentTag.asset_sha256)
        .distinct()
        .subquery()
    )
    rows = db.scalars(
        select(Asset)
        .where(Asset.is_canonical.is_(True))
        .where(~Asset.sha256.in_(select(tagged_subq.c.asset_sha256)))
        .order_by(Asset.created_at_utc.asc())
    ).all()
    return list(rows)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def persist_content_tags(
    db: Session,
    results: list[TaggingResult],
) -> int:
    """Upsert content tags for each result.  Returns total rows written."""
    written = 0
    for result in results:
        for label, score in result.tags:
            tag_type = get_tag_type(label)
            existing = db.scalars(
                select(AssetContentTag)
                .where(AssetContentTag.asset_sha256 == result.asset_sha256)
                .where(AssetContentTag.tag == label)
            ).first()
            if existing is not None:
                existing.confidence_score = score
                existing.tag_type = tag_type
            else:
                db.add(
                    AssetContentTag(
                        asset_sha256=result.asset_sha256,
                        tag=label,
                        confidence_score=score,
                        tag_type=tag_type,
                    )
                )
            written += 1
    db.commit()
    return written


# ---------------------------------------------------------------------------
# Main batch runner
# ---------------------------------------------------------------------------

def run_content_tagging(
    assets: list[Asset],
    vault_root: Path,
    *,
    min_confidence: float,
    max_per_asset: int,
) -> BatchTaggingOutcome:
    """Infer content tags for a list of assets; return outcome (does not persist)."""
    ensure_content_tag_runtime_available()
    outcome = BatchTaggingOutcome()
    for asset in assets:
        image_path = vault_root / asset.vault_path
        try:
            tags = _infer_tags(
                image_path,
                min_confidence=min_confidence,
                max_per_asset=max_per_asset,
            )
            outcome.tagged.append(TaggingResult(asset_sha256=asset.sha256, tags=tags))
        except Exception as exc:  # noqa: BLE001
            reason = type(exc).__name__
            logger.warning("Content tagging failed for %s: %s", asset.sha256, exc)
            outcome.failures.append((asset.sha256, reason))
    return outcome
