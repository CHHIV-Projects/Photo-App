"""Near-duplicate suggestion queue service for milestone 12.12."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.duplicate_rejection import DuplicateRejection
from app.services.duplicates.lineage import IMAGE_EXTENSIONS
from app.services.photos.display_url_service import build_asset_display_url_contract

MAX_SUGGESTION_DISTANCE = 15
HIGH_MAX_DISTANCE = 5
MEDIUM_MAX_DISTANCE = 10


@dataclass(frozen=True)
class SuggestionAssetSummary:
    asset_sha256: str
    filename: str
    image_url: str | None
    display_url: str | None
    original_url: str
    has_display_preview: bool
    display_source: str
    duplicate_group_id: int | None
    quality_score: float | None


@dataclass(frozen=True)
class DuplicateSuggestionSummary:
    confidence: str
    distance: int
    asset_a: SuggestionAssetSummary
    asset_b: SuggestionAssetSummary


@dataclass(frozen=True)
class DuplicateSuggestionListResult:
    total_count: int
    items: list[DuplicateSuggestionSummary]


def _canonical_pair(sha_a: str, sha_b: str) -> tuple[str, str]:
    return (sha_a, sha_b) if sha_a <= sha_b else (sha_b, sha_a)


def _hamming_distance_int(hash_a: int, hash_b: int) -> int:
    return (hash_a ^ hash_b).bit_count()


def confidence_bucket_for_distance(distance: int) -> str | None:
    if distance < 0:
        return None
    if distance <= HIGH_MAX_DISTANCE:
        return "high"
    if distance <= MEDIUM_MAX_DISTANCE:
        return "medium"
    if distance <= MAX_SUGGESTION_DISTANCE:
        return "low"
    return None


def _confidence_rank(confidence: str) -> int:
    if confidence == "high":
        return 0
    if confidence == "medium":
        return 1
    return 2


def list_duplicate_suggestions(
    db_session: Session,
    *,
    offset: int = 0,
    limit: int = 50,
) -> DuplicateSuggestionListResult:
    """Generate deterministic pair suggestions excluding same-group and rejected pairs."""
    bounded_limit = max(1, min(limit, 200))
    bounded_offset = max(0, offset)

    assets = list(
        db_session.scalars(
            select(Asset)
            .where(Asset.phash.is_not(None), Asset.extension.in_(sorted(IMAGE_EXTENSIONS)))
            .order_by(Asset.sha256.asc())
        ).all()
    )
    if len(assets) < 2:
        return DuplicateSuggestionListResult(total_count=0, items=[])

    rejected_pairs = {
        _canonical_pair(row.asset_sha256_a, row.asset_sha256_b)
        for row in db_session.scalars(select(DuplicateRejection)).all()
    }

    candidates: list[DuplicateSuggestionSummary] = []
    for index, left in enumerate(assets):
        try:
            left_hash = int(left.phash or "", 16)
        except ValueError:
            continue

        for right in assets[index + 1 :]:
            if (
                left.duplicate_group_id is not None
                and right.duplicate_group_id is not None
                and left.duplicate_group_id == right.duplicate_group_id
            ):
                continue

            canonical_pair = _canonical_pair(left.sha256, right.sha256)
            if canonical_pair in rejected_pairs:
                continue

            try:
                right_hash = int(right.phash or "", 16)
            except ValueError:
                continue

            distance = _hamming_distance_int(left_hash, right_hash)
            confidence = confidence_bucket_for_distance(distance)
            if confidence is None:
                continue

            candidates.append(
                DuplicateSuggestionSummary(
                    confidence=confidence,
                    distance=distance,
                    asset_a=SuggestionAssetSummary(
                        asset_sha256=left.sha256,
                        filename=left.original_filename,
                        **(lambda contract: {
                            "image_url": contract.image_url,
                            "display_url": contract.display_url,
                            "original_url": contract.original_url,
                            "has_display_preview": contract.has_display_preview,
                            "display_source": contract.display_source,
                        })(
                            build_asset_display_url_contract(
                                sha256=left.sha256,
                                extension=left.extension,
                                display_preview_path=left.display_preview_path,
                            )
                        ),
                        duplicate_group_id=left.duplicate_group_id,
                        quality_score=left.quality_score,
                    ),
                    asset_b=SuggestionAssetSummary(
                        asset_sha256=right.sha256,
                        filename=right.original_filename,
                        **(lambda contract: {
                            "image_url": contract.image_url,
                            "display_url": contract.display_url,
                            "original_url": contract.original_url,
                            "has_display_preview": contract.has_display_preview,
                            "display_source": contract.display_source,
                        })(
                            build_asset_display_url_contract(
                                sha256=right.sha256,
                                extension=right.extension,
                                display_preview_path=right.display_preview_path,
                            )
                        ),
                        duplicate_group_id=right.duplicate_group_id,
                        quality_score=right.quality_score,
                    ),
                )
            )

    candidates.sort(
        key=lambda item: (
            _confidence_rank(item.confidence),
            item.distance,
            item.asset_a.asset_sha256,
            item.asset_b.asset_sha256,
        )
    )

    return DuplicateSuggestionListResult(
        total_count=len(candidates),
        items=candidates[bounded_offset : bounded_offset + bounded_limit],
    )


def reject_duplicate_pair(
    db_session: Session,
    *,
    asset_sha256_a: str,
    asset_sha256_b: str,
) -> bool:
    """Persist symmetric pair rejection. Returns True if inserted, False if already present."""
    left, right = _canonical_pair(asset_sha256_a, asset_sha256_b)
    existing = db_session.scalar(
        select(DuplicateRejection).where(
            DuplicateRejection.asset_sha256_a == left,
            DuplicateRejection.asset_sha256_b == right,
        )
    )
    if existing is not None:
        return False

    db_session.add(DuplicateRejection(asset_sha256_a=left, asset_sha256_b=right))
    db_session.commit()
    return True
