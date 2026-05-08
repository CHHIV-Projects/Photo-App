"""Deterministic Live Photo still/motion pairing service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath

from sqlalchemy import and_, delete, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.live_photo_pair import LivePhotoPair
from app.models.provenance import Provenance

STILL_EXTENSIONS = {".heic", ".heif", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}
MOTION_EXTENSIONS = {".mov"}
PAIRING_METHOD = "basename"
HIGH_CONFIDENCE_MAX_SECONDS = 10
SUSPICIOUS_MAX_SECONDS = 60


@dataclass(frozen=True)
class PairCandidate:
    ingestion_source_id: int
    source_relative_dir: str
    source_basename: str
    still_asset_sha256: str
    motion_asset_sha256: str
    time_delta_seconds: int | None
    confidence: str


@dataclass(frozen=True)
class LivePhotoPairingResult:
    scanned_rows: int
    candidate_groups: int
    inserted: int
    updated: int
    unchanged: int
    removed_stale: int
    skipped_missing_source: int
    skipped_ambiguous: int
    skipped_suspicious_delta: int
    generated_at_utc: str
    sample_pairs: list[dict[str, str | int | None]]


def _normalize_relative_path(path_value: str) -> str:
    normalized = path_value.strip().replace("\\", "/")
    return normalized.strip("/")


def _extract_group_parts(relative_path: str) -> tuple[str, str] | None:
    normalized = _normalize_relative_path(relative_path)
    if not normalized:
        return None

    posix_path = PurePosixPath(normalized)
    filename = posix_path.name
    if not filename:
        return None

    basename = PurePosixPath(filename).stem.strip().lower()
    if not basename:
        return None

    parent = str(posix_path.parent)
    source_relative_dir = "" if parent == "." else parent.lower()
    return source_relative_dir, basename


def _role_for_extension(extension: str | None) -> str | None:
    normalized = (extension or "").strip().lower()
    if not normalized:
        return None
    if not normalized.startswith("."):
        normalized = f".{normalized}"

    if normalized in STILL_EXTENSIONS:
        return "still"
    if normalized in MOTION_EXTENSIONS:
        return "motion"
    return None


def _to_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _pair_confidence(
    still_captured_at: datetime | None,
    motion_captured_at: datetime | None,
    still_capture_time_trust: str | None,
    motion_capture_time_trust: str | None,
) -> tuple[str, int | None, bool]:
    if still_captured_at is None or motion_captured_at is None:
        return "high", None, False

    # Enforce strict timestamp safeguards only when both timestamps are high-trust.
    if (still_capture_time_trust or "unknown") != "high" or (motion_capture_time_trust or "unknown") != "high":
        return "high", None, False

    still_utc = _to_utc_datetime(still_captured_at)
    motion_utc = _to_utc_datetime(motion_captured_at)
    if still_utc is None or motion_utc is None:
        return "high", None, False

    delta = int(abs((still_utc - motion_utc).total_seconds()))
    if delta > SUSPICIOUS_MAX_SECONDS:
        return "skip", delta, True
    if delta > HIGH_CONFIDENCE_MAX_SECONDS:
        return "medium", delta, False
    return "high", delta, False


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_row_sample(candidate: PairCandidate) -> dict[str, str | int | None]:
    return {
        "source_id": candidate.ingestion_source_id,
        "source_relative_dir": candidate.source_relative_dir,
        "source_basename": candidate.source_basename,
        "still_asset_sha256": candidate.still_asset_sha256,
        "motion_asset_sha256": candidate.motion_asset_sha256,
        "confidence": candidate.confidence,
        "time_delta_seconds": candidate.time_delta_seconds,
    }


def run_live_photo_pairing(db_session: Session) -> LivePhotoPairingResult:
    rows = db_session.execute(
        select(
            Provenance.ingestion_source_id,
            Provenance.source_relative_path,
            Provenance.source_path,
            Asset.sha256,
            Asset.extension,
            Asset.captured_at,
            Asset.capture_time_trust,
        ).join(Asset, Asset.sha256 == Provenance.asset_sha256)
    ).all()

    grouped: dict[tuple[int, str, str], dict[str, dict[str, tuple[datetime | None, str | None]]]] = {}
    scanned_rows = 0
    skipped_missing_source = 0

    for row in rows:
        role = _role_for_extension(row.extension)
        if role is None:
            continue

        scanned_rows += 1
        if row.ingestion_source_id is None:
            skipped_missing_source += 1
            continue

        key_path = row.source_relative_path or row.source_path
        if not key_path:
            continue

        parts = _extract_group_parts(key_path)
        if parts is None:
            continue

        source_relative_dir, source_basename = parts
        key = (int(row.ingestion_source_id), source_relative_dir, source_basename)
        bucket = grouped.setdefault(key, {"still": {}, "motion": {}})

        bucket_for_role = bucket[role]
        existing_value = bucket_for_role.get(row.sha256)
        if existing_value is None:
            bucket_for_role[row.sha256] = (row.captured_at, row.capture_time_trust)

    candidates: list[PairCandidate] = []
    skipped_ambiguous = 0
    skipped_suspicious_delta = 0

    for key, bucket in grouped.items():
        still_items = list(bucket["still"].items())
        motion_items = list(bucket["motion"].items())

        if len(still_items) != 1 or len(motion_items) != 1:
            skipped_ambiguous += 1
            continue

        still_sha, still_info = still_items[0]
        motion_sha, motion_info = motion_items[0]
        still_captured_at, still_capture_time_trust = still_info
        motion_captured_at, motion_capture_time_trust = motion_info

        confidence, delta_seconds, is_suspicious = _pair_confidence(
            still_captured_at,
            motion_captured_at,
            still_capture_time_trust,
            motion_capture_time_trust,
        )
        if is_suspicious:
            skipped_suspicious_delta += 1
            continue

        candidates.append(
            PairCandidate(
                ingestion_source_id=key[0],
                source_relative_dir=key[1],
                source_basename=key[2],
                still_asset_sha256=still_sha,
                motion_asset_sha256=motion_sha,
                time_delta_seconds=delta_seconds,
                confidence=confidence,
            )
        )

    deduped_candidates: list[PairCandidate] = []
    candidate_by_still: dict[str, PairCandidate] = {}
    candidate_by_motion: dict[str, PairCandidate] = {}
    for candidate in sorted(
        candidates,
        key=lambda item: (item.ingestion_source_id, item.source_relative_dir, item.source_basename),
    ):
        still_conflict = candidate_by_still.get(candidate.still_asset_sha256)
        motion_conflict = candidate_by_motion.get(candidate.motion_asset_sha256)

        if still_conflict is not None and still_conflict.motion_asset_sha256 != candidate.motion_asset_sha256:
            skipped_ambiguous += 1
            continue
        if motion_conflict is not None and motion_conflict.still_asset_sha256 != candidate.still_asset_sha256:
            skipped_ambiguous += 1
            continue
        if still_conflict is not None or motion_conflict is not None:
            continue

        candidate_by_still[candidate.still_asset_sha256] = candidate
        candidate_by_motion[candidate.motion_asset_sha256] = candidate
        deduped_candidates.append(candidate)

    existing_pairs = list(db_session.scalars(select(LivePhotoPair)).all())
    existing_by_still = {pair.still_asset_sha256: pair for pair in existing_pairs}
    candidate_stills = {candidate.still_asset_sha256 for candidate in deduped_candidates}

    inserted = 0
    updated = 0
    unchanged = 0

    for candidate in deduped_candidates:
        existing = existing_by_still.get(candidate.still_asset_sha256)
        if existing is None:
            db_session.add(
                LivePhotoPair(
                    still_asset_sha256=candidate.still_asset_sha256,
                    motion_asset_sha256=candidate.motion_asset_sha256,
                    ingestion_source_id=candidate.ingestion_source_id,
                    source_relative_dir=candidate.source_relative_dir,
                    source_basename=candidate.source_basename,
                    pairing_method=PAIRING_METHOD,
                    confidence=candidate.confidence,
                    time_delta_seconds=candidate.time_delta_seconds,
                )
            )
            inserted += 1
            continue

        if (
            existing.motion_asset_sha256 == candidate.motion_asset_sha256
            and existing.ingestion_source_id == candidate.ingestion_source_id
            and existing.source_relative_dir == candidate.source_relative_dir
            and existing.source_basename == candidate.source_basename
            and existing.confidence == candidate.confidence
            and existing.time_delta_seconds == candidate.time_delta_seconds
            and existing.pairing_method == PAIRING_METHOD
        ):
            unchanged += 1
            continue

        existing.motion_asset_sha256 = candidate.motion_asset_sha256
        existing.ingestion_source_id = candidate.ingestion_source_id
        existing.source_relative_dir = candidate.source_relative_dir
        existing.source_basename = candidate.source_basename
        existing.pairing_method = PAIRING_METHOD
        existing.confidence = candidate.confidence
        existing.time_delta_seconds = candidate.time_delta_seconds
        updated += 1

    stale_still_shas = set(existing_by_still.keys()) - candidate_stills
    removed_stale = 0
    if stale_still_shas:
        removed_stale = db_session.execute(
            delete(LivePhotoPair).where(LivePhotoPair.still_asset_sha256.in_(stale_still_shas))
        ).rowcount or 0

    # Cleanup orphan rows where either side no longer exists.
    valid_assets_subq = select(Asset.sha256)
    db_session.execute(
        delete(LivePhotoPair).where(
            and_(
                LivePhotoPair.still_asset_sha256.not_in(valid_assets_subq),
            )
        )
    )
    db_session.execute(
        delete(LivePhotoPair).where(
            and_(
                LivePhotoPair.motion_asset_sha256.not_in(valid_assets_subq),
            )
        )
    )

    db_session.commit()

    return LivePhotoPairingResult(
        scanned_rows=scanned_rows,
        candidate_groups=len(grouped),
        inserted=inserted,
        updated=updated,
        unchanged=unchanged,
        removed_stale=removed_stale,
        skipped_missing_source=skipped_missing_source,
        skipped_ambiguous=skipped_ambiguous,
        skipped_suspicious_delta=skipped_suspicious_delta,
        generated_at_utc=_iso_utc_now(),
        sample_pairs=[_build_row_sample(item) for item in deduped_candidates[:25]],
    )
