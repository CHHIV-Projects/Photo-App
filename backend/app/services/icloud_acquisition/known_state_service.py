"""Preflight candidate parsing and known-state evaluation for iCloud acquisition."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.provenance import Provenance


KNOWN_STATE_STAGED = "staged_known"
KNOWN_STATE_INGESTED = "ingested_known"
KNOWN_STATE_VAULT_VERIFIED = "vault_verified_known"
KNOWN_STATE_UNKNOWN = "unknown"

CAUGHT_UP_LIKELY = "likely_caught_up"
CAUGHT_UP_PARTIAL = "partial_window_only"
CAUGHT_UP_UNKNOWN = "unknown"


@dataclass(frozen=True)
class PreflightCandidate:
    raw_line: str
    normalized_source_relative_path: str | None
    unknown_identity: bool


@dataclass(frozen=True)
class CandidateKnownState:
    raw_line: str
    normalized_source_relative_path: str | None
    unknown_identity: bool
    staged_known: bool
    ingested_known: bool
    vault_verified_known: bool
    already_known: bool
    known_state: str


@dataclass(frozen=True)
class KnownStateSummary:
    candidate_count: int
    already_known_count: int
    staged_known_count: int
    ingested_known_count: int
    vault_verified_known_count: int
    unknown_identity_count: int
    candidates: list[CandidateKnownState]


_LOG_PREFIX = re.compile(r"^(?:debug|info|warn|warning|error|trace)\b", re.IGNORECASE)


def _normalize_relative_path(text: str) -> str:
    value = text.strip().strip("\"").strip("'")
    value = value.replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    value = value.lstrip("/")
    return value.strip()


def _looks_like_candidate_line(raw_line: str) -> bool:
    line = raw_line.strip()
    if not line:
        return False
    if _LOG_PREFIX.match(line):
        return False
    if line.lower().startswith("usage:"):
        return False
    return True


def parse_preflight_candidates(stdout_text: str | None, stderr_text: str | None) -> list[PreflightCandidate]:
    candidates: list[PreflightCandidate] = []
    combined = "\n".join(part for part in [stdout_text or "", stderr_text or ""] if part)
    if not combined.strip():
        return candidates

    for raw_line in combined.splitlines():
        if not _looks_like_candidate_line(raw_line):
            continue

        normalized = _normalize_relative_path(raw_line)
        # Conservative identity confidence: require a normalized path with filename extension.
        filename = Path(normalized).name
        has_extension = "." in filename and not filename.endswith(".")
        unknown_identity = not bool(normalized) or not has_extension
        candidates.append(
            PreflightCandidate(
                raw_line=raw_line,
                normalized_source_relative_path=None if unknown_identity else normalized,
                unknown_identity=unknown_identity,
            )
        )

    return candidates


def evaluate_known_state(
    db_session: Session,
    *,
    ingestion_source_id: int,
    staging_root: Path,
    candidates: list[PreflightCandidate],
) -> KnownStateSummary:
    rows: list[CandidateKnownState] = []

    paths = sorted(
        {
            candidate.normalized_source_relative_path
            for candidate in candidates
            if candidate.normalized_source_relative_path is not None
        }
    )

    provenance_by_path: dict[str, Provenance] = {}
    if paths:
        lookup_set = {path for path in paths}
        lookup_set.update(path.replace("/", "\\") for path in paths)
        provenance_rows = db_session.execute(
            select(Provenance).where(
                and_(
                    Provenance.ingestion_source_id == ingestion_source_id,
                    Provenance.source_relative_path.in_(lookup_set),
                )
            )
        ).scalars().all()
        for row in provenance_rows:
            normalized = _normalize_relative_path(row.source_relative_path or "")
            if normalized:
                provenance_by_path[normalized] = row

    asset_hashes = {
        row.asset_sha256 for row in provenance_by_path.values() if (row.asset_sha256 or "").strip()
    }
    assets_by_hash: dict[str, Asset] = {}
    if asset_hashes:
        asset_rows = db_session.execute(select(Asset).where(Asset.sha256.in_(sorted(asset_hashes)))).scalars().all()
        for row in asset_rows:
            assets_by_hash[row.sha256] = row

    for candidate in candidates:
        normalized = candidate.normalized_source_relative_path
        staged_known = False
        ingested_known = False
        vault_verified_known = False
        already_known = False
        known_state = KNOWN_STATE_UNKNOWN

        if normalized is not None:
            staged_known = (staging_root / Path(normalized)).exists()
            provenance = provenance_by_path.get(normalized)
            if provenance is not None:
                ingested_known = True
                already_known = True
                known_state = KNOWN_STATE_INGESTED

                asset_hash = (provenance.asset_sha256 or "").strip().lower()
                asset = assets_by_hash.get(asset_hash)
                if asset is not None and (asset.vault_path or "").strip():
                    vault_path = Path(asset.vault_path).expanduser()
                    if not vault_path.is_absolute():
                        vault_path = (Path(__file__).resolve().parents[4] / vault_path).resolve()
                    else:
                        vault_path = vault_path.resolve()
                    if vault_path.exists():
                        vault_verified_known = True
                        known_state = KNOWN_STATE_VAULT_VERIFIED

            elif staged_known:
                known_state = KNOWN_STATE_STAGED

        rows.append(
            CandidateKnownState(
                raw_line=candidate.raw_line,
                normalized_source_relative_path=normalized,
                unknown_identity=candidate.unknown_identity,
                staged_known=staged_known,
                ingested_known=ingested_known,
                vault_verified_known=vault_verified_known,
                already_known=already_known,
                known_state=known_state,
            )
        )

    return KnownStateSummary(
        candidate_count=len(rows),
        already_known_count=sum(1 for row in rows if row.already_known),
        staged_known_count=sum(1 for row in rows if row.staged_known),
        ingested_known_count=sum(1 for row in rows if row.ingested_known),
        vault_verified_known_count=sum(1 for row in rows if row.vault_verified_known),
        unknown_identity_count=sum(1 for row in rows if row.unknown_identity),
        candidates=rows,
    )


def derive_caught_up_status(
    *,
    preflight_ok: bool,
    preflight_candidate_count: int,
    unknown_identity_count: int,
    all_candidates_already_known: bool,
    download_skipped_due_to_all_known: bool,
) -> str:
    if not preflight_ok:
        return CAUGHT_UP_UNKNOWN
    if preflight_candidate_count <= 0:
        return CAUGHT_UP_UNKNOWN
    if unknown_identity_count > 0:
        return CAUGHT_UP_PARTIAL
    if all_candidates_already_known and download_skipped_due_to_all_known:
        return CAUGHT_UP_LIKELY
    return CAUGHT_UP_PARTIAL
