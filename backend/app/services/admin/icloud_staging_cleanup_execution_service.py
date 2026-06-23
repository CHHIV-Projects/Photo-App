"""Guarded planning and execution for local iCloud staging cleanup."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import threading
from typing import Any, Callable

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.icloud_staging_cleanup_run import IcloudStagingCleanupRun
from app.models.ingestion_source import IngestionSource
from app.models.provenance import Provenance
from app.models.source_intake_run import SourceIntakeRun
from app.services.admin.icloud_staging_cleanup_schema import ensure_icloud_staging_cleanup_schema
from app.services.icloud_path_service import resolve_icloud_staging_path
from app.services.ingestion.pipeline_orchestrator import resolve_runtime_path


RUNNING_STATUSES = {"pending", "running", "stop_requested"}
PLANNER_VERSION = "2"
DRY_RUN_FRESHNESS_SECONDS = 10 * 60
EXECUTION_CONFIRMATION_PHRASE = "DELETE LOCAL STAGING COPIES"
SKIP_SAMPLE_LIMIT = 10
REPORT_PREVIEW_LIMIT = 100
PROGRESS_UPDATE_INTERVAL = 25


class CleanupBusyError(RuntimeError):
    """Raised when a cleanup run is already active."""


class SourceIntakeActiveError(RuntimeError):
    """Raised when source intake is active for the selected source."""


class CleanupValidationError(ValueError):
    """Raised when source configuration is invalid for cleanup."""

    def __init__(self, message: str, *, code: str = "INVALID_CLEANUP_SOURCE") -> None:
        super().__init__(message)
        self.code = code


class CleanupAuthorizationError(ValueError):
    """Raised when guarded execution authorization fails."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class CleanupRunSnapshot:
    run_id: int
    status: str
    source_id: int | None
    source_label: str | None
    source_root_path: str | None
    dry_run: bool
    started_at: str | None
    finished_at: str | None
    elapsed_seconds: float | None
    eligible_count: int
    deleted_count: int
    skipped_count: int
    total_bytes_eligible: int
    total_bytes_deleted: int
    total_files: int
    processed_files: int
    current_stage: str | None
    protected_count: int
    verification_failed_count: int
    file_missing_count: int
    delete_failed_count: int
    manifest_fingerprint: str | None
    planner_version: str | None
    preview_expires_at: str | None
    authorized_dry_run_id: int | None
    authorization_consumed_at: str | None
    skipped_reasons: dict[str, int]
    skipped_samples: dict[str, list[str]]
    report_path: str | None
    error_message: str | None


@dataclass(frozen=True)
class CleanupSourceReadiness:
    source_id: int
    ready: bool
    canonical_staging_path: str | None
    blocking_reasons: list[tuple[str, str]]


@dataclass(frozen=True)
class ValidatedCleanupSource:
    source_id: int
    source_label: str
    canonical_root: Path


@dataclass(frozen=True)
class CleanupCandidate:
    source_id: int
    relative_path: str
    absolute_path: str
    size_bytes: int
    staged_mtime_ns: int
    staged_sha256: str
    asset_sha256: str
    vault_path: str
    vault_sha256: str

    def manifest_row(self) -> dict[str, Any]:
        return {
            "category": "eligible",
            "relative_path": self.relative_path,
            "size_bytes": self.size_bytes,
            "staged_mtime_ns": self.staged_mtime_ns,
            "staged_sha256": self.staged_sha256,
            "asset_sha256": self.asset_sha256,
            "vault_path": self.vault_path,
            "vault_sha256": self.vault_sha256,
        }


@dataclass(frozen=True)
class CleanupPlanIssue:
    category: str
    reason: str
    relative_path: str
    detail: str | None = None
    size_bytes: int | None = None
    mtime_ns: int | None = None

    def manifest_row(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "reason": self.reason,
            "relative_path": self.relative_path,
            "size_bytes": self.size_bytes,
            "mtime_ns": self.mtime_ns,
        }

    def report_row(self) -> dict[str, Any]:
        return {**self.manifest_row(), "detail": self.detail}


@dataclass
class CleanupPlan:
    source: ValidatedCleanupSource
    eligible: list[CleanupCandidate] = field(default_factory=list)
    issues: list[CleanupPlanIssue] = field(default_factory=list)
    manifest_fingerprint: str = ""

    @property
    def total_files(self) -> int:
        return len(self.eligible) + len(self.issues)

    @property
    def total_bytes_eligible(self) -> int:
        return sum(item.size_bytes for item in self.eligible)


ProgressCallback = Callable[[str, int, int], None]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _resolve_exports_root() -> Path:
    return (_project_root() / "storage" / "exports" / "icloud").resolve()


def _resolve_vault_root() -> Path:
    return resolve_runtime_path(settings.vault_path).resolve()


def _normalize_relative(path: str) -> str:
    return path.replace("\\", "/").lstrip("/")


def _to_iso_utc(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _json_dict(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _snapshot_from_row(row: IcloudStagingCleanupRun) -> CleanupRunSnapshot:
    return CleanupRunSnapshot(
        run_id=row.id,
        status=row.status,
        source_id=row.ingestion_source_id,
        source_label=row.source_label,
        source_root_path=row.source_root_path,
        dry_run=bool(row.dry_run),
        started_at=_to_iso_utc(row.started_at),
        finished_at=_to_iso_utc(row.finished_at),
        elapsed_seconds=row.elapsed_seconds,
        eligible_count=int(row.eligible_count or 0),
        deleted_count=int(row.deleted_count or 0),
        skipped_count=int(row.skipped_count or 0),
        total_bytes_eligible=int(row.total_bytes_eligible or 0),
        total_bytes_deleted=int(row.total_bytes_deleted or 0),
        total_files=int(row.total_files or 0),
        processed_files=int(row.processed_files or 0),
        current_stage=row.current_stage,
        protected_count=int(row.protected_count or 0),
        verification_failed_count=int(row.verification_failed_count or 0),
        file_missing_count=int(row.file_missing_count or 0),
        delete_failed_count=int(row.delete_failed_count or 0),
        manifest_fingerprint=row.manifest_fingerprint,
        planner_version=row.planner_version,
        preview_expires_at=_to_iso_utc(row.preview_expires_at),
        authorized_dry_run_id=row.authorized_dry_run_id,
        authorization_consumed_at=_to_iso_utc(row.authorization_consumed_at),
        skipped_reasons={k: int(v) for k, v in _json_dict(row.skipped_reasons_json).items()},
        skipped_samples={
            str(k): [str(item) for item in v][:SKIP_SAMPLE_LIMIT]
            for k, v in _json_dict(row.skipped_samples_json).items()
            if isinstance(v, list)
        },
        report_path=row.report_path,
        error_message=row.error_message,
    )


def reset_stale_cleanup_runs(db: Session) -> int:
    """Mark stale running rows as failed after app restarts."""
    stale_rows = db.execute(
        select(IcloudStagingCleanupRun).where(IcloudStagingCleanupRun.status.in_(tuple(RUNNING_STATUSES)))
    ).scalars().all()
    now = datetime.now(UTC)
    for row in stale_rows:
        row.status = "failed"
        row.current_stage = "interrupted"
        row.started_at = row.started_at or now
        row.finished_at = now
        row.elapsed_seconds = float((now - _as_utc(row.started_at)).total_seconds())
        row.error_message = "Run interrupted before completion (service restart or crash)."
    if stale_rows:
        db.commit()
    return len(stale_rows)


def get_cleanup_status(db: Session, *, source_id: int | None = None) -> CleanupRunSnapshot | None:
    stmt = select(IcloudStagingCleanupRun)
    if source_id is not None:
        stmt = stmt.where(IcloudStagingCleanupRun.ingestion_source_id == source_id)
    row = db.execute(
        stmt.order_by(IcloudStagingCleanupRun.created_at.desc(), IcloudStagingCleanupRun.id.desc()).limit(1)
    ).scalar_one_or_none()
    return None if row is None else _snapshot_from_row(row)


def get_latest_cleanup_dry_run(db: Session, *, source_id: int) -> CleanupRunSnapshot | None:
    row = db.execute(
        select(IcloudStagingCleanupRun)
        .where(
            and_(
                IcloudStagingCleanupRun.ingestion_source_id == source_id,
                IcloudStagingCleanupRun.dry_run.is_(True),
            )
        )
        .order_by(IcloudStagingCleanupRun.created_at.desc(), IcloudStagingCleanupRun.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    return None if row is None else _snapshot_from_row(row)


def get_cleanup_source_readiness(db: Session, *, source_id: int) -> CleanupSourceReadiness:
    try:
        source = _validate_cleanup_source(db, source_id=source_id)
    except CleanupValidationError as exc:
        return CleanupSourceReadiness(
            source_id=source_id,
            ready=False,
            canonical_staging_path=None,
            blocking_reasons=[(exc.code, str(exc))],
        )
    return CleanupSourceReadiness(
        source_id=source_id,
        ready=True,
        canonical_staging_path=str(source.canonical_root),
        blocking_reasons=[],
    )


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (ValueError, OSError):
        return False


def _resolve_existing_directory(path_value: str, *, field_name: str) -> Path:
    candidate = Path(path_value).expanduser()
    candidate = candidate.resolve() if candidate.is_absolute() else (_project_root() / candidate).resolve()
    if not candidate.exists() or not candidate.is_dir():
        raise CleanupValidationError(
            f"{field_name} does not exist or is not a directory: {candidate}",
            code="STAGING_PATH_MISSING",
        )
    return candidate


def _validate_cleanup_source(db: Session, *, source_id: int) -> ValidatedCleanupSource:
    source = db.get(IngestionSource, source_id)
    if source is None:
        raise CleanupValidationError(f"Source {source_id} does not exist.", code="SOURCE_NOT_FOUND")
    if (source.profile_status or "").strip().lower() != "active":
        raise CleanupValidationError("Only active Source Profiles can run cleanup.", code="PROFILE_NOT_ACTIVE")
    if (source.source_type or "").strip().lower() != "cloud_export":
        raise CleanupValidationError("Cleanup requires a cloud_export source.", code="NOT_ICLOUD_PROFILE")
    if (source.cloud_provider or "").strip().lower() != "icloud":
        raise CleanupValidationError("Cleanup requires an iCloud Source Profile.", code="NOT_ICLOUD_PROFILE")
    if (source.acquisition_method or "").strip().lower() != "icloudpd":
        raise CleanupValidationError("Cleanup requires the icloudpd acquisition method.", code="INVALID_ACQUISITION_METHOD")

    source_root_value = (source.source_root_path or "").strip()
    managed_root_value = (source.managed_staging_path or "").strip()
    if not source_root_value or not managed_root_value:
        raise CleanupValidationError(
            "Source root and managed staging path are both required.",
            code="STAGING_PATH_MISSING",
        )

    source_root = _resolve_existing_directory(source_root_value, field_name="Source root")
    managed_root = _resolve_existing_directory(managed_root_value, field_name="Managed staging path")
    expected_root = resolve_icloud_staging_path(source.source_label).resolve()
    exports_root = _resolve_exports_root()

    if not _is_within(source_root, exports_root) or not _is_within(managed_root, exports_root):
        raise CleanupValidationError(
            "Cleanup path is outside storage/exports/icloud.",
            code="APPROVED_ROOT_BLOCKED",
        )
    if source_root != managed_root or source_root != expected_root:
        raise CleanupValidationError(
            "Source root, managed staging path, and canonical iCloud staging path do not match.",
            code="STAGING_PATH_MISMATCH",
        )

    return ValidatedCleanupSource(
        source_id=source.id,
        source_label=source.source_label,
        canonical_root=source_root,
    )


def _collect_report_evidence(source_id: int, source_root: Path) -> tuple[set[str], set[str]]:
    reports_dir = (_project_root() / "storage" / "logs" / "source_intake_reports").resolve()
    failure_paths: set[str] = set()
    deferred_paths: set[str] = set()
    if not reports_dir.exists():
        return failure_paths, deferred_paths

    for report_file in sorted(reports_dir.glob("source_intake_*.json")):
        try:
            payload = json.loads(report_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if int(payload.get("ingestion_source_id") or -1) != source_id:
            continue
        for failed in payload.get("failure_details") or []:
            if isinstance(failed, dict):
                relative = _path_to_relative(failed.get("source_path"), source_root)
                if relative:
                    failure_paths.add(relative)
        for deferred in payload.get("deferred_unready_sample") or []:
            relative = _path_to_relative(deferred, source_root)
            if relative:
                deferred_paths.add(relative)
    return failure_paths, deferred_paths


def _path_to_relative(path_value: Any, source_root: Path) -> str | None:
    if not isinstance(path_value, str) or not path_value.strip():
        return None
    try:
        candidate = Path(path_value).resolve()
        if not _is_within(candidate, source_root):
            return None
        return _normalize_relative(str(candidate.relative_to(source_root)))
    except Exception:
        return None


def _fetch_provenance_map(
    db: Session,
    source_id: int,
    relative_paths: list[str],
) -> dict[str, list[Provenance]]:
    result: dict[str, list[Provenance]] = defaultdict(list)
    for idx in range(0, len(relative_paths), 500):
        lookup_set: set[str] = set()
        for path in relative_paths[idx : idx + 500]:
            lookup_set.add(path)
            lookup_set.add(path.replace("/", "\\"))
        rows = db.execute(
            select(Provenance).where(
                and_(
                    Provenance.ingestion_source_id == source_id,
                    Provenance.source_relative_path.in_(lookup_set),
                )
            )
        ).scalars().all()
        for row in rows:
            result[_normalize_relative(row.source_relative_path or "")].append(row)
    return result


def _fetch_assets_map(db: Session, hashes: set[str]) -> dict[str, Asset]:
    result: dict[str, Asset] = {}
    hash_list = sorted(hashes)
    for idx in range(0, len(hash_list), 500):
        rows = db.execute(select(Asset).where(Asset.sha256.in_(hash_list[idx : idx + 500]))).scalars().all()
        for row in rows:
            result[row.sha256.lower()] = row
    return result


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_file_stable(path: Path) -> tuple[str, os.stat_result]:
    before = path.stat()
    digest = _sha256_file(path)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise OSError(f"File changed while hashing: {path}")
    return digest, after


def _issue_for_path(
    category: str,
    reason: str,
    relative_path: str,
    *,
    path: Path | None = None,
    detail: str | None = None,
) -> CleanupPlanIssue:
    size_bytes: int | None = None
    mtime_ns: int | None = None
    if path is not None:
        try:
            stat = path.stat()
            size_bytes = int(stat.st_size)
            mtime_ns = int(stat.st_mtime_ns)
        except OSError:
            pass
    return CleanupPlanIssue(category, reason, relative_path, detail, size_bytes, mtime_ns)


def _compute_manifest_fingerprint(plan: CleanupPlan) -> str:
    rows = [item.manifest_row() for item in plan.eligible]
    rows.extend(item.manifest_row() for item in plan.issues)
    rows.sort(key=lambda item: (str(item.get("relative_path")), str(item.get("category")), str(item.get("reason", ""))))
    encoded = json.dumps(
        {"planner_version": PLANNER_VERSION, "files": rows},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _build_cleanup_plan(
    db: Session,
    *,
    source: ValidatedCleanupSource,
    progress_callback: ProgressCallback | None = None,
) -> CleanupPlan:
    root = source.canonical_root.resolve()
    discovered = sorted(
        [path for path in root.rglob("*") if path.is_file() or path.is_symlink()],
        key=lambda path: _normalize_relative(str(path)),
    )
    relative_paths: list[str] = []
    for path in discovered:
        try:
            relative_paths.append(_normalize_relative(str(path.relative_to(root))))
        except ValueError:
            relative_paths.append(_normalize_relative(str(path)))

    provenance_by_rel = _fetch_provenance_map(db, source.source_id, relative_paths)
    provenance_hashes = {
        (row.asset_sha256 or "").strip().lower()
        for rows in provenance_by_rel.values()
        for row in rows
        if (row.asset_sha256 or "").strip()
    }
    assets_by_hash = _fetch_assets_map(db, provenance_hashes)
    failure_paths, deferred_paths = _collect_report_evidence(source.source_id, root)
    vault_root = _resolve_vault_root()
    vault_hash_cache: dict[str, str] = {}
    plan = CleanupPlan(source=source)

    if progress_callback:
        progress_callback("planning", len(discovered), 0)

    for index, path in enumerate(discovered, start=1):
        try:
            relative_path = _normalize_relative(str(path.relative_to(root)))
        except ValueError:
            relative_path = _normalize_relative(str(path))

        if progress_callback and (index == 1 or index % PROGRESS_UPDATE_INTERVAL == 0 or index == len(discovered)):
            progress_callback("planning", len(discovered), index)

        try:
            resolved = path.resolve(strict=True)
        except FileNotFoundError:
            plan.issues.append(_issue_for_path("file_missing", "file_missing", relative_path))
            continue
        except OSError as exc:
            plan.issues.append(_issue_for_path("verification_failed", "path_resolution_failed", relative_path, detail=str(exc)))
            continue

        if path.is_symlink() or not resolved.is_file() or not _is_within(resolved, root):
            plan.issues.append(_issue_for_path("verification_failed", "staging_path_unsafe", relative_path, path=path))
            continue

        provenance_rows = provenance_by_rel.get(relative_path, [])
        distinct_hashes = {
            (row.asset_sha256 or "").strip().lower()
            for row in provenance_rows
            if (row.asset_sha256 or "").strip()
        }
        if not distinct_hashes:
            reason = "failed_or_deferred_evidence" if relative_path in failure_paths or relative_path in deferred_paths else "no_provenance"
            plan.issues.append(_issue_for_path("protected", reason, relative_path, path=resolved))
            continue
        if len(distinct_hashes) != 1:
            plan.issues.append(_issue_for_path("verification_failed", "ambiguous_provenance", relative_path, path=resolved))
            continue

        asset_hash = next(iter(distinct_hashes))
        asset = assets_by_hash.get(asset_hash)
        if asset is None:
            plan.issues.append(_issue_for_path("verification_failed", "asset_missing", relative_path, path=resolved))
            continue

        try:
            staged_hash, staged_stat = _sha256_file_stable(resolved)
        except FileNotFoundError:
            plan.issues.append(_issue_for_path("file_missing", "file_missing", relative_path))
            continue
        except OSError as exc:
            plan.issues.append(_issue_for_path("verification_failed", "staged_hash_failed", relative_path, path=resolved, detail=str(exc)))
            continue
        if staged_hash != asset_hash:
            plan.issues.append(_issue_for_path("verification_failed", "staged_hash_mismatch", relative_path, path=resolved))
            continue

        vault_path_value = (asset.vault_path or "").strip()
        if not vault_path_value:
            plan.issues.append(_issue_for_path("verification_failed", "vault_missing", relative_path, path=resolved))
            continue
        vault_path = Path(vault_path_value).expanduser()
        vault_path = vault_path.resolve() if vault_path.is_absolute() else (_project_root() / vault_path).resolve()
        if not _is_within(vault_path, vault_root) or vault_path.is_symlink() or not vault_path.is_file():
            plan.issues.append(_issue_for_path("verification_failed", "vault_path_unsafe_or_missing", relative_path, path=resolved))
            continue
        try:
            cache_key = str(vault_path)
            vault_hash = vault_hash_cache.get(cache_key)
            if vault_hash is None:
                vault_hash, _ = _sha256_file_stable(vault_path)
                vault_hash_cache[cache_key] = vault_hash
        except OSError as exc:
            plan.issues.append(_issue_for_path("verification_failed", "vault_hash_failed", relative_path, path=resolved, detail=str(exc)))
            continue
        if vault_hash != asset_hash:
            plan.issues.append(_issue_for_path("verification_failed", "vault_hash_mismatch", relative_path, path=resolved))
            continue
        if relative_path in failure_paths or relative_path in deferred_paths:
            plan.issues.append(_issue_for_path("protected", "conflicting_status_evidence", relative_path, path=resolved))
            continue

        plan.eligible.append(
            CleanupCandidate(
                source_id=source.source_id,
                relative_path=relative_path,
                absolute_path=str(resolved),
                size_bytes=int(staged_stat.st_size),
                staged_mtime_ns=int(staged_stat.st_mtime_ns),
                staged_sha256=staged_hash,
                asset_sha256=asset_hash,
                vault_path=str(vault_path),
                vault_sha256=vault_hash,
            )
        )

    plan.manifest_fingerprint = _compute_manifest_fingerprint(plan)
    return plan


def _active_cleanup(db: Session) -> IcloudStagingCleanupRun | None:
    return db.execute(
        select(IcloudStagingCleanupRun)
        .where(IcloudStagingCleanupRun.status.in_(tuple(RUNNING_STATUSES)))
        .order_by(IcloudStagingCleanupRun.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def _assert_no_active_cleanup_or_source_intake(db: Session, source_id: int) -> None:
    active = _active_cleanup(db)
    if active is not None:
        raise CleanupBusyError(f"Cleanup run {active.id} is already active.")
    active_source_intake = db.execute(
        select(SourceIntakeRun.id).where(SourceIntakeRun.status.in_(tuple(RUNNING_STATUSES))).limit(1)
    ).scalar_one_or_none()
    if active_source_intake is not None:
        raise SourceIntakeActiveError(f"Source Intake run {active_source_intake} is active.")


def _new_run(
    *,
    source: ValidatedCleanupSource,
    dry_run: bool,
    created_by: str | None,
    authorized_dry_run_id: int | None = None,
) -> IcloudStagingCleanupRun:
    return IcloudStagingCleanupRun(
        status="pending",
        ingestion_source_id=source.source_id,
        source_label=source.source_label,
        source_root_path=str(source.canonical_root),
        dry_run=dry_run,
        started_at=datetime.now(UTC),
        eligible_count=0,
        deleted_count=0,
        skipped_count=0,
        total_bytes_eligible=0,
        total_bytes_deleted=0,
        total_files=0,
        processed_files=0,
        current_stage="pending",
        protected_count=0,
        verification_failed_count=0,
        file_missing_count=0,
        delete_failed_count=0,
        skipped_reasons_json=json.dumps({}),
        skipped_samples_json=json.dumps({}),
        planner_version=PLANNER_VERSION,
        authorized_dry_run_id=authorized_dry_run_id,
        created_by=created_by,
    )


def start_cleanup_run(
    db: Session,
    *,
    source_id: int,
    dry_run: bool,
    created_by: str | None = None,
) -> CleanupRunSnapshot:
    """Start dry-run planning. Live execution must use the guarded endpoint."""
    ensure_icloud_staging_cleanup_schema(db)
    if not dry_run:
        raise CleanupAuthorizationError(
            "Direct dry_run=false cleanup is disabled. Use guarded cleanup execution.",
            code="GUARDED_EXECUTION_REQUIRED",
        )
    _assert_no_active_cleanup_or_source_intake(db, source_id)
    source = _validate_cleanup_source(db, source_id=source_id)
    run = _new_run(source=source, dry_run=True, created_by=created_by)
    db.add(run)
    db.commit()
    db.refresh(run)
    threading.Thread(
        target=_run_cleanup_background,
        kwargs={"run_id": run.id, "source_id": source_id, "dry_run_run_id": None},
        daemon=True,
        name=f"icloud-cleanup-dry-run-{run.id}",
    ).start()
    return _snapshot_from_row(run)


def start_cleanup_execution(
    db: Session,
    *,
    source_id: int,
    dry_run_run_id: int,
    explicit_confirmation: str,
    created_by: str | None = None,
) -> CleanupRunSnapshot:
    ensure_icloud_staging_cleanup_schema(db)
    if explicit_confirmation != EXECUTION_CONFIRMATION_PHRASE:
        raise CleanupAuthorizationError("Explicit confirmation phrase does not match.", code="CONFIRMATION_REQUIRED")
    _assert_no_active_cleanup_or_source_intake(db, source_id)
    source = _validate_cleanup_source(db, source_id=source_id)
    dry_run = db.get(IcloudStagingCleanupRun, dry_run_run_id)
    now = datetime.now(UTC)
    if dry_run is None:
        raise CleanupAuthorizationError("Dry-run authorization was not found.", code="DRY_RUN_NOT_FOUND")
    if dry_run.ingestion_source_id != source_id:
        raise CleanupAuthorizationError("Dry run belongs to a different source.", code="DRY_RUN_SOURCE_MISMATCH")
    if not dry_run.dry_run or dry_run.status != "completed":
        raise CleanupAuthorizationError("Dry run is not successfully completed.", code="DRY_RUN_NOT_COMPLETED")
    if dry_run.authorization_consumed_at is not None:
        raise CleanupAuthorizationError("Dry run authorization was already consumed.", code="DRY_RUN_ALREADY_CONSUMED")
    if dry_run.planner_version != PLANNER_VERSION or not dry_run.manifest_fingerprint:
        raise CleanupAuthorizationError("Dry run uses obsolete or incomplete planner data.", code="DRY_RUN_INVALID")
    if dry_run.eligible_count <= 0:
        raise CleanupAuthorizationError("Dry run has no eligible local staging files.", code="DRY_RUN_EMPTY")
    expires_at = _as_utc(dry_run.preview_expires_at)
    if expires_at is None or expires_at <= now:
        raise CleanupAuthorizationError("Dry run has expired. Run a new preview.", code="DRY_RUN_EXPIRED")
    if Path(dry_run.source_root_path or "").resolve() != source.canonical_root:
        raise CleanupAuthorizationError("Dry-run staging path no longer matches the source.", code="DRY_RUN_PATH_MISMATCH")

    execution = _new_run(
        source=source,
        dry_run=False,
        created_by=created_by,
        authorized_dry_run_id=dry_run.id,
    )
    dry_run.authorization_consumed_at = now
    db.add(execution)
    db.commit()
    db.refresh(execution)
    threading.Thread(
        target=_run_cleanup_background,
        kwargs={"run_id": execution.id, "source_id": source_id, "dry_run_run_id": dry_run.id},
        daemon=True,
        name=f"icloud-cleanup-execution-{execution.id}",
    ).start()
    return _snapshot_from_row(execution)


def _plan_issue_counts(plan: CleanupPlan) -> tuple[Counter[str], dict[str, list[str]]]:
    reasons = Counter(item.reason for item in plan.issues)
    samples: dict[str, list[str]] = defaultdict(list)
    for item in plan.issues:
        if len(samples[item.reason]) < SKIP_SAMPLE_LIMIT:
            samples[item.reason].append(item.relative_path)
    return reasons, dict(samples)


def _update_row_from_plan(row: IcloudStagingCleanupRun, plan: CleanupPlan) -> None:
    reasons, samples = _plan_issue_counts(plan)
    row.total_files = plan.total_files
    row.processed_files = plan.total_files
    row.eligible_count = len(plan.eligible)
    row.skipped_count = len(plan.issues)
    row.total_bytes_eligible = plan.total_bytes_eligible
    row.protected_count = sum(1 for item in plan.issues if item.category == "protected")
    row.verification_failed_count = sum(1 for item in plan.issues if item.category == "verification_failed")
    row.file_missing_count = sum(1 for item in plan.issues if item.category == "file_missing")
    row.manifest_fingerprint = plan.manifest_fingerprint
    row.planner_version = PLANNER_VERSION
    row.skipped_reasons_json = json.dumps(dict(reasons), sort_keys=True)
    row.skipped_samples_json = json.dumps(samples, sort_keys=True)


def _report_paths(run_id: int) -> tuple[Path, Path]:
    reports_dir = (_project_root() / "storage" / "logs" / "icloud_cleanup_reports").resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    report = reports_dir / f"icloud_cleanup_{now.strftime('%Y%m%d_%H%M%S')}_run{run_id}.json"
    return report, report.with_suffix(".events.jsonl")


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(path)


def _append_audit_event(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _report_payload(
    *,
    run_id: int,
    plan: CleanupPlan,
    dry_run: bool,
    status: str,
    started_at: datetime,
    authorized_dry_run_id: int | None,
    deleted: list[dict[str, Any]],
    execution_issues: list[CleanupPlanIssue],
    journal_path: Path | None,
    error_message: str | None = None,
) -> dict[str, Any]:
    all_issues = [*plan.issues, *execution_issues]
    reasons = Counter(item.reason for item in all_issues)
    return {
        "report_type": "icloud_staging_cleanup",
        "planner_version": PLANNER_VERSION,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "source_id": plan.source.source_id,
        "source_label": plan.source.source_label,
        "source_root_path": str(plan.source.canonical_root),
        "dry_run": dry_run,
        "status": status,
        "started_at_utc": started_at.isoformat(),
        "authorized_dry_run_id": authorized_dry_run_id,
        "manifest_fingerprint": plan.manifest_fingerprint,
        "audit_journal_path": None if journal_path is None else str(journal_path),
        "error_message": error_message,
        "counts": {
            "total_files": plan.total_files,
            "eligible_count": len(plan.eligible),
            "deleted_count": len(deleted),
            "skipped_count": len(all_issues),
            "protected_count": sum(1 for item in all_issues if item.category == "protected"),
            "verification_failed_count": sum(1 for item in all_issues if item.category == "verification_failed"),
            "file_missing_count": sum(1 for item in all_issues if item.category == "file_missing"),
            "delete_failed_count": sum(1 for item in all_issues if item.category == "delete_failed"),
            "total_bytes_eligible": plan.total_bytes_eligible,
            "total_bytes_deleted": sum(int(item["size_bytes"]) for item in deleted),
        },
        "skipped_reasons": dict(reasons),
        "eligible_files": [item.manifest_row() for item in plan.eligible],
        "deleted_files": deleted,
        "skipped_files": [item.report_row() for item in all_issues],
        "preview": {
            "eligible_files": [item.relative_path for item in plan.eligible[:REPORT_PREVIEW_LIMIT]],
            "deleted_files": [item["relative_path"] for item in deleted[:REPORT_PREVIEW_LIMIT]],
            "skipped_files": [item.report_row() for item in all_issues[:REPORT_PREVIEW_LIMIT]],
        },
    }


def _revalidate_candidate(candidate: CleanupCandidate, source: ValidatedCleanupSource) -> CleanupPlanIssue | None:
    path = Path(candidate.absolute_path)
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError:
        return _issue_for_path("file_missing", "file_missing", candidate.relative_path)
    except OSError as exc:
        return _issue_for_path("verification_failed", "path_resolution_failed", candidate.relative_path, detail=str(exc))
    if candidate.source_id != source.source_id or path.is_symlink() or not resolved.is_file() or not _is_within(resolved, source.canonical_root):
        return _issue_for_path("verification_failed", "staging_path_unsafe", candidate.relative_path, path=path)
    try:
        relative = _normalize_relative(str(resolved.relative_to(source.canonical_root)))
        staged_hash, stat = _sha256_file_stable(resolved)
    except FileNotFoundError:
        return _issue_for_path("file_missing", "file_missing", candidate.relative_path)
    except OSError as exc:
        return _issue_for_path("verification_failed", "staged_revalidation_failed", candidate.relative_path, detail=str(exc))
    if relative != candidate.relative_path or int(stat.st_size) != candidate.size_bytes or staged_hash != candidate.asset_sha256:
        return _issue_for_path("verification_failed", "staged_file_changed", candidate.relative_path, path=resolved)

    vault_path = Path(candidate.vault_path)
    vault_root = _resolve_vault_root()
    if vault_path.is_symlink() or not vault_path.is_file() or not _is_within(vault_path, vault_root):
        return _issue_for_path("verification_failed", "vault_path_unsafe_or_missing", candidate.relative_path, path=resolved)
    try:
        vault_hash, _ = _sha256_file_stable(vault_path)
        if vault_hash != candidate.asset_sha256:
            return _issue_for_path("verification_failed", "vault_hash_mismatch", candidate.relative_path, path=resolved)
    except OSError as exc:
        return _issue_for_path("verification_failed", "vault_hash_failed", candidate.relative_path, path=resolved, detail=str(exc))
    return None


def _cleanup_empty_subdirectories(source_root: Path) -> None:
    descendants = sorted(
        [path for path in source_root.rglob("*") if path.is_dir() and not path.is_symlink() and path != source_root],
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for directory in descendants:
        try:
            next(directory.iterdir())
        except StopIteration:
            try:
                directory.rmdir()
            except OSError:
                pass
        except OSError:
            pass


def _run_cleanup_background(*, run_id: int, source_id: int, dry_run_run_id: int | None) -> None:
    db = SessionLocal()
    started = datetime.now(UTC)
    deleted: list[dict[str, Any]] = []
    execution_issues: list[CleanupPlanIssue] = []
    report_path: Path | None = None
    journal_path: Path | None = None
    try:
        row = db.get(IcloudStagingCleanupRun, run_id)
        if row is None:
            return
        row.status = "running"
        row.current_stage = "validating_source"
        row.started_at = started
        db.commit()
        source = _validate_cleanup_source(db, source_id=source_id)

        def update_progress(stage: str, total: int, processed: int) -> None:
            row.current_stage = stage
            row.total_files = total
            row.processed_files = processed
            db.commit()

        plan = _build_cleanup_plan(db, source=source, progress_callback=update_progress)
        _update_row_from_plan(row, plan)

        if row.dry_run:
            report_path, _ = _report_paths(run_id)
            _atomic_write_json(
                report_path,
                _report_payload(
                    run_id=run_id,
                    plan=plan,
                    dry_run=True,
                    status="completed",
                    started_at=started,
                    authorized_dry_run_id=None,
                    deleted=[],
                    execution_issues=[],
                    journal_path=None,
                ),
            )
            finished = datetime.now(UTC)
            row.status = "completed"
            row.current_stage = "completed"
            row.finished_at = finished
            row.elapsed_seconds = float((finished - started).total_seconds())
            row.preview_expires_at = finished + timedelta(seconds=DRY_RUN_FRESHNESS_SECONDS)
            row.report_path = str(report_path)
            row.error_message = None
            db.commit()
            return

        approved = db.get(IcloudStagingCleanupRun, dry_run_run_id)
        approved_is_valid = bool(
            approved is not None
            and approved.dry_run
            and approved.status == "completed"
            and approved.ingestion_source_id == source_id
            and approved.planner_version == PLANNER_VERSION
            and approved.authorization_consumed_at is not None
            and _as_utc(approved.preview_expires_at) is not None
            and _as_utc(approved.preview_expires_at) > started
        )
        if not approved_is_valid or approved.manifest_fingerprint != plan.manifest_fingerprint:
            report_path, _ = _report_paths(run_id)
            error = "Candidate manifest changed after dry run. No files were deleted; run a new dry run."
            _atomic_write_json(
                report_path,
                _report_payload(
                    run_id=run_id,
                    plan=plan,
                    dry_run=False,
                    status="failed",
                    started_at=started,
                    authorized_dry_run_id=dry_run_run_id,
                    deleted=[],
                    execution_issues=[],
                    journal_path=None,
                    error_message=error,
                ),
            )
            row.status = "failed"
            row.current_stage = "manifest_mismatch"
            row.finished_at = datetime.now(UTC)
            row.elapsed_seconds = float((row.finished_at - started).total_seconds())
            row.report_path = str(report_path)
            row.error_message = error
            db.commit()
            return

        report_path, journal_path = _report_paths(run_id)
        _atomic_write_json(
            report_path,
            _report_payload(
                run_id=run_id,
                plan=plan,
                dry_run=False,
                status="running",
                started_at=started,
                authorized_dry_run_id=dry_run_run_id,
                deleted=[],
                execution_issues=[],
                journal_path=journal_path,
            ),
        )
        journal_path.touch(exist_ok=True)
        row.report_path = str(report_path)
        row.current_stage = "deleting"
        row.processed_files = len(plan.issues)
        db.commit()

        for index, candidate in enumerate(plan.eligible, start=1):
            issue = _revalidate_candidate(candidate, source)
            if issue is not None:
                execution_issues.append(issue)
                event = {"at_utc": datetime.now(UTC).isoformat(), "outcome": issue.category, "relative_path": issue.relative_path, "reason": issue.reason}
            else:
                try:
                    Path(candidate.absolute_path).unlink(missing_ok=False)
                    deleted_item = {"relative_path": candidate.relative_path, "size_bytes": candidate.size_bytes, "asset_sha256": candidate.asset_sha256}
                    deleted.append(deleted_item)
                    event = {"at_utc": datetime.now(UTC).isoformat(), "outcome": "deleted", **deleted_item}
                except FileNotFoundError:
                    issue = _issue_for_path("file_missing", "file_missing", candidate.relative_path)
                    execution_issues.append(issue)
                    event = {"at_utc": datetime.now(UTC).isoformat(), "outcome": "file_missing", "relative_path": candidate.relative_path, "reason": issue.reason}
                except OSError as exc:
                    issue = _issue_for_path("delete_failed", "delete_failed", candidate.relative_path, detail=str(exc))
                    execution_issues.append(issue)
                    event = {"at_utc": datetime.now(UTC).isoformat(), "outcome": "delete_failed", "relative_path": candidate.relative_path, "reason": str(exc)}

            _append_audit_event(journal_path, event)
            if index % PROGRESS_UPDATE_INTERVAL == 0 or index == len(plan.eligible):
                row.processed_files = len(plan.issues) + index
                row.deleted_count = len(deleted)
                row.total_bytes_deleted = sum(int(item["size_bytes"]) for item in deleted)
                db.commit()

        if deleted:
            _cleanup_empty_subdirectories(source.canonical_root)

        all_issues = [*plan.issues, *execution_issues]
        reasons = Counter(item.reason for item in all_issues)
        samples: dict[str, list[str]] = defaultdict(list)
        for item in all_issues:
            if len(samples[item.reason]) < SKIP_SAMPLE_LIMIT:
                samples[item.reason].append(item.relative_path)
        has_execution_errors = bool(execution_issues)
        final_status = "completed_with_errors" if has_execution_errors else "completed"
        final_report_error: str | None = None
        try:
            _atomic_write_json(
                report_path,
                _report_payload(
                    run_id=run_id,
                    plan=plan,
                    dry_run=False,
                    status=final_status,
                    started_at=started,
                    authorized_dry_run_id=dry_run_run_id,
                    deleted=deleted,
                    execution_issues=execution_issues,
                    journal_path=journal_path,
                ),
            )
        except OSError as exc:
            final_status = "completed_with_errors"
            final_report_error = f"Final report update failed; audit journal retained: {exc}"

        finished = datetime.now(UTC)
        row.status = final_status
        row.current_stage = "completed"
        row.finished_at = finished
        row.elapsed_seconds = float((finished - started).total_seconds())
        row.processed_files = plan.total_files
        row.deleted_count = len(deleted)
        row.skipped_count = len(all_issues)
        row.total_bytes_deleted = sum(int(item["size_bytes"]) for item in deleted)
        row.protected_count = sum(1 for item in all_issues if item.category == "protected")
        row.verification_failed_count = sum(1 for item in all_issues if item.category == "verification_failed")
        row.file_missing_count = sum(1 for item in all_issues if item.category == "file_missing")
        row.delete_failed_count = sum(1 for item in all_issues if item.category == "delete_failed")
        row.skipped_reasons_json = json.dumps(dict(reasons), sort_keys=True)
        row.skipped_samples_json = json.dumps(dict(samples), sort_keys=True)
        row.error_message = final_report_error
        db.commit()

    except Exception as exc:
        row = db.get(IcloudStagingCleanupRun, run_id)
        if row is not None:
            finished = datetime.now(UTC)
            row.status = "completed_with_errors" if deleted else "failed"
            row.current_stage = "failed"
            row.finished_at = finished
            row.started_at = row.started_at or started
            row.elapsed_seconds = float((finished - _as_utc(row.started_at)).total_seconds())
            row.deleted_count = len(deleted)
            row.total_bytes_deleted = sum(int(item["size_bytes"]) for item in deleted)
            row.error_message = str(exc)[:2000]
            if report_path is not None:
                row.report_path = str(report_path)
            db.commit()
    finally:
        db.close()
