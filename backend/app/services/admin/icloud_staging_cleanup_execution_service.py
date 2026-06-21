"""Execution service for iCloud staging cleanup runs."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import threading
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.icloud_staging_cleanup_run import IcloudStagingCleanupRun
from app.models.ingestion_source import IngestionSource
from app.models.provenance import Provenance
from app.models.source_intake_run import SourceIntakeRun

RUNNING_STATUSES = {"pending", "running", "stop_requested"}
SKIP_SAMPLE_LIMIT = 10
REPORT_PREVIEW_LIMIT = 100


class CleanupBusyError(RuntimeError):
    """Raised when a cleanup run is already active."""


class SourceIntakeActiveError(RuntimeError):
    """Raised when source intake is active for the selected source."""


class CleanupValidationError(ValueError):
    """Raised when source configuration is invalid for cleanup."""


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
    skipped_reasons: dict[str, int]
    skipped_samples: dict[str, list[str]]
    report_path: str | None
    error_message: str | None


@dataclass
class _SkipEntry:
    reason: str
    relative_path: str


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _normalize_relative(path: str) -> str:
    return path.replace("\\", "/").lstrip("/")


def _to_iso_utc(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()


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

    count = 0
    now = datetime.now(UTC)
    for row in stale_rows:
        row.status = "failed"
        if row.started_at is None:
            row.started_at = now
        row.finished_at = now
        row.elapsed_seconds = float((now - row.started_at).total_seconds())
        row.error_message = "Run interrupted before completion (service restart or crash)."
        count += 1

    if count:
        db.commit()
    return count


def get_cleanup_status(db: Session, *, source_id: int | None = None) -> CleanupRunSnapshot | None:
    stmt = select(IcloudStagingCleanupRun)
    if source_id is not None:
        stmt = stmt.where(IcloudStagingCleanupRun.ingestion_source_id == source_id)

    row = db.execute(
        stmt.order_by(IcloudStagingCleanupRun.created_at.desc(), IcloudStagingCleanupRun.id.desc()).limit(1)
    ).scalar_one_or_none()
    if row is None:
        return None
    return _snapshot_from_row(row)


def start_cleanup_run(
    db: Session,
    *,
    source_id: int,
    dry_run: bool,
    created_by: str | None = None,
) -> CleanupRunSnapshot:
    active = db.execute(
        select(IcloudStagingCleanupRun)
        .where(IcloudStagingCleanupRun.status.in_(tuple(RUNNING_STATUSES)))
        .order_by(IcloudStagingCleanupRun.created_at.desc(), IcloudStagingCleanupRun.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if active is not None:
        raise CleanupBusyError(f"Cleanup run {active.id} is already active.")

    active_source_intake = db.execute(
        select(SourceIntakeRun.id).where(
            and_(
                SourceIntakeRun.ingestion_source_id == source_id,
                SourceIntakeRun.status.in_(tuple(RUNNING_STATUSES)),
            )
        )
    ).scalar_one_or_none()
    if active_source_intake is not None:
        raise SourceIntakeActiveError(
            f"Source intake run {active_source_intake} is active for source {source_id}."
        )

    source = db.get(IngestionSource, source_id)
    if source is None:
        raise CleanupValidationError(f"Source {source_id} does not exist.")
    if (source.source_type or "").strip().lower() != "cloud_export":
        raise CleanupValidationError("Only cloud_export sources can be cleaned up.")

    source_root_path = (source.source_root_path or "").strip()
    if not source_root_path:
        raise CleanupValidationError("Source root path is empty.")

    resolved_source_root = _resolve_source_root(Path(source_root_path))
    exports_root = _resolve_exports_root()
    if not _is_within(resolved_source_root, exports_root):
        raise CleanupValidationError(
            "Source root path is not under storage/exports/icloud and cannot be cleaned up safely."
        )

    now = datetime.now(UTC)
    run = IcloudStagingCleanupRun(
        status="pending",
        ingestion_source_id=source.id,
        source_label=source.source_label,
        source_root_path=str(resolved_source_root),
        dry_run=bool(dry_run),
        started_at=now,
        eligible_count=0,
        deleted_count=0,
        skipped_count=0,
        total_bytes_eligible=0,
        total_bytes_deleted=0,
        skipped_reasons_json=json.dumps({}),
        skipped_samples_json=json.dumps({}),
        created_by=created_by,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    thread = threading.Thread(
        target=_run_cleanup_background,
        kwargs={
            "run_id": run.id,
            "source_id": source.id,
            "source_label": source.source_label,
            "source_root": resolved_source_root,
            "dry_run": bool(dry_run),
        },
        daemon=True,
    )
    thread.start()

    return _snapshot_from_row(run)


def _resolve_exports_root() -> Path:
    return (_project_root() / "storage" / "exports" / "icloud").resolve()


def _resolve_source_root(source_root_path: Path) -> Path:
    if not str(source_root_path).strip():
        raise CleanupValidationError("Source root path is empty.")

    candidate = source_root_path.expanduser()
    if not candidate.is_absolute():
        candidate = (_project_root() / candidate).resolve()
    else:
        candidate = candidate.resolve()

    if candidate.exists():
        return candidate

    candidate_str = str(candidate)
    marker = f"backend{Path.sep}storage{Path.sep}"
    if marker in candidate_str:
        fixed = Path(candidate_str.replace(marker, f"storage{Path.sep}", 1)).resolve()
        if fixed.exists():
            return fixed

    raise CleanupValidationError(f"Source root path does not exist: {candidate}")


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _collect_report_evidence(source_id: int, source_root: Path) -> tuple[set[str], set[str], bool]:
    reports_dir = (_project_root() / "storage" / "logs" / "source_intake_reports").resolve()
    if not reports_dir.exists():
        return set(), set(), False

    failure_paths: set[str] = set()
    deferred_paths: set[str] = set()
    found = False

    for report_file in sorted(reports_dir.glob("source_intake_*.json")):
        try:
            payload = json.loads(report_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        if int(payload.get("ingestion_source_id") or -1) != source_id:
            continue

        found = True
        for failed in payload.get("failure_details") or []:
            if not isinstance(failed, dict):
                continue
            source_path = failed.get("source_path")
            rel = _path_to_relative(source_path, source_root)
            if rel:
                failure_paths.add(rel)

        for deferred in payload.get("deferred_unready_sample") or []:
            rel = _path_to_relative(deferred, source_root)
            if rel:
                deferred_paths.add(rel)

    return failure_paths, deferred_paths, found


def _path_to_relative(path_value: Any, source_root: Path) -> str | None:
    if not isinstance(path_value, str) or not path_value.strip():
        return None
    candidate = Path(path_value)
    try:
        candidate_resolved = candidate.resolve()
    except Exception:
        return None

    if not _is_within(candidate_resolved, source_root):
        return None

    return _normalize_relative(str(candidate_resolved.relative_to(source_root)))


def _fetch_provenance_map(db: Session, source_id: int, relative_paths: list[str]) -> dict[str, Provenance]:
    """Build a normalized-path → Provenance map.

    The DB may store paths with either Windows backslashes or POSIX forward
    slashes depending on when/where ingestion ran.  We query using both forms
    so the lookup succeeds regardless of which separator was persisted.
    """
    result: dict[str, Provenance] = {}
    if not relative_paths:
        return result

    chunk_size = 500
    for idx in range(0, len(relative_paths), chunk_size):
        norm_chunk = relative_paths[idx : idx + chunk_size]
        # Also include the backslash variant for paths stored on Windows
        lookup_set: set[str] = set()
        for p in norm_chunk:
            lookup_set.add(p)
            lookup_set.add(p.replace("/", "\\"))
        rows = db.execute(
            select(Provenance).where(
                and_(
                    Provenance.ingestion_source_id == source_id,
                    Provenance.source_relative_path.in_(lookup_set),
                )
            )
        ).scalars().all()
        for row in rows:
            result[_normalize_relative(row.source_relative_path or "")] = row

    return result


def _fetch_assets_map(db: Session, hashes: set[str]) -> dict[str, Asset]:
    result: dict[str, Asset] = {}
    if not hashes:
        return result

    hash_list = sorted(hashes)
    chunk_size = 500
    for idx in range(0, len(hash_list), chunk_size):
        chunk = hash_list[idx : idx + chunk_size]
        rows = db.execute(select(Asset).where(Asset.sha256.in_(chunk))).scalars().all()
        for row in rows:
            result[row.sha256] = row

    return result


def _resolve_vault_path(vault_path: str) -> Path:
    candidate = Path(vault_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (_project_root() / candidate).resolve()


def _run_cleanup_background(
    *,
    run_id: int,
    source_id: int,
    source_label: str | None,
    source_root: Path,
    dry_run: bool,
) -> None:
    db = SessionLocal()
    started = datetime.now(UTC)
    try:
        row = db.get(IcloudStagingCleanupRun, run_id)
        if row is None:
            return
        row.status = "running"
        row.started_at = started
        db.commit()

        exports_root = _resolve_exports_root()
        source_root_resolved = source_root.resolve()

        skipped: list[_SkipEntry] = []
        eligible: list[dict[str, Any]] = []
        deleted: list[dict[str, Any]] = []

        if not _is_within(source_root_resolved, exports_root):
            row.status = "failed"
            row.error_message = "source_not_under_icloud_exports_root"
            row.finished_at = datetime.now(UTC)
            row.elapsed_seconds = float((row.finished_at - started).total_seconds())
            db.commit()
            return

        all_files = [p for p in source_root_resolved.rglob("*") if p.is_file()]
        relative_paths = [_normalize_relative(str(p.relative_to(source_root_resolved))) for p in all_files]

        provenance_by_rel = _fetch_provenance_map(db, source_id, relative_paths)
        hash_candidates = {
            prov.asset_sha256
            for prov in provenance_by_rel.values()
            if prov.asset_sha256 and isinstance(prov.asset_sha256, str)
        }
        assets_by_hash = _fetch_assets_map(db, hash_candidates)
        failure_paths, deferred_paths, has_report_evidence = _collect_report_evidence(source_id, source_root_resolved)

        for file_path in all_files:
            try:
                file_resolved = file_path.resolve()
                if not _is_within(file_resolved, source_root_resolved):
                    skipped.append(_SkipEntry("source_not_under_icloud_exports_root", _normalize_relative(str(file_path))))
                    continue

                relative_path = _normalize_relative(str(file_resolved.relative_to(source_root_resolved)))
                if not has_report_evidence:
                    skipped.append(_SkipEntry("status_evidence_missing", relative_path))
                    continue

                has_failure_or_deferred = relative_path in failure_paths or relative_path in deferred_paths

                prov = provenance_by_rel.get(relative_path)
                if prov is None:
                    reason = "failed_or_deferred_evidence" if has_failure_or_deferred else "no_provenance"
                    skipped.append(_SkipEntry(reason, relative_path))
                    continue

                asset_hash = (prov.asset_sha256 or "").strip().lower()
                if not asset_hash:
                    skipped.append(_SkipEntry("no_provenance", relative_path))
                    continue

                asset = assets_by_hash.get(asset_hash)
                if asset is None:
                    skipped.append(_SkipEntry("asset_missing", relative_path))
                    continue

                vault_path_value = (asset.vault_path or "").strip()
                if not vault_path_value:
                    skipped.append(_SkipEntry("vault_missing", relative_path))
                    continue

                vault_path = _resolve_vault_path(vault_path_value)
                if not vault_path.exists():
                    skipped.append(_SkipEntry("vault_missing", relative_path))
                    continue

                if has_failure_or_deferred:
                    skipped.append(_SkipEntry("conflicting_status_evidence", relative_path))
                    continue

                size_bytes = int(file_resolved.stat().st_size)
                eligible.append({
                    "relative_path": relative_path,
                    "absolute_path": str(file_resolved),
                    "size_bytes": size_bytes,
                })

                if dry_run:
                    continue

                if not file_resolved.exists():
                    skipped.append(_SkipEntry("file_missing", relative_path))
                    eligible.pop()
                    continue

                file_resolved.unlink(missing_ok=False)
                deleted.append({
                    "relative_path": relative_path,
                    "absolute_path": str(file_resolved),
                    "size_bytes": size_bytes,
                })

            except FileNotFoundError:
                skipped.append(_SkipEntry("file_missing", _normalize_relative(str(file_path))))
            except Exception:
                skipped.append(_SkipEntry("status_evidence_missing", _normalize_relative(str(file_path))))

        if not dry_run:
            try:
                _cleanup_empty_subdirectories(source_root_resolved)
            except Exception:
                pass  # Directory cleanup is best-effort; don't fail the run

        skipped_reason_counts = Counter(entry.reason for entry in skipped)
        skipped_samples: dict[str, list[str]] = defaultdict(list)
        for entry in skipped:
            if len(skipped_samples[entry.reason]) < SKIP_SAMPLE_LIMIT:
                skipped_samples[entry.reason].append(entry.relative_path)

        report_path = _write_report(
            run_id=run_id,
            source_id=source_id,
            source_label=source_label,
            source_root=source_root_resolved,
            dry_run=dry_run,
            started_at=started,
            eligible=eligible,
            deleted=deleted,
            skipped=skipped,
            skipped_reason_counts=dict(skipped_reason_counts),
            skipped_samples=dict(skipped_samples),
        )

        finished = datetime.now(UTC)
        row.status = "completed"
        row.finished_at = finished
        row.elapsed_seconds = float((finished - started).total_seconds())
        row.eligible_count = len(eligible)
        row.deleted_count = len(deleted)
        row.skipped_count = len(skipped)
        row.total_bytes_eligible = int(sum(item["size_bytes"] for item in eligible))
        row.total_bytes_deleted = int(sum(item["size_bytes"] for item in deleted))
        row.skipped_reasons_json = json.dumps(dict(skipped_reason_counts), sort_keys=True)
        row.skipped_samples_json = json.dumps(dict(skipped_samples), sort_keys=True)
        row.report_path = report_path
        row.error_message = None
        db.commit()

    except Exception as exc:
        row = db.get(IcloudStagingCleanupRun, run_id)
        if row is not None:
            finished = datetime.now(UTC)
            row.status = "failed"
            row.finished_at = finished
            if row.started_at is None:
                row.started_at = started
            row.elapsed_seconds = float((finished - row.started_at).total_seconds())
            row.error_message = str(exc)[:2000]
            db.commit()
    finally:
        db.close()


def _cleanup_empty_subdirectories(source_root: Path) -> None:
    # Remove empty descendants only; keep source_root itself for operator continuity.
    descendants = sorted(
        [p for p in source_root.rglob("*") if p.is_dir() and p != source_root],
        key=lambda p: len(p.parts),
        reverse=True,
    )
    for directory in descendants:
        try:
            next(directory.iterdir())
            continue
        except StopIteration:
            try:
                directory.rmdir()
            except Exception:
                pass
        except Exception:
            continue


def _write_report(
    *,
    run_id: int,
    source_id: int,
    source_label: str | None,
    source_root: Path,
    dry_run: bool,
    started_at: datetime,
    eligible: list[dict[str, Any]],
    deleted: list[dict[str, Any]],
    skipped: list[_SkipEntry],
    skipped_reason_counts: dict[str, int],
    skipped_samples: dict[str, list[str]],
) -> str:
    reports_dir = (_project_root() / "storage" / "logs" / "icloud_cleanup_reports").resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)
    filename = f"icloud_cleanup_{now.strftime('%Y%m%d_%H%M%S')}_run{run_id}.json"
    report_path = reports_dir / filename

    payload = {
        "report_type": "icloud_staging_cleanup",
        "generated_at_utc": now.isoformat(),
        "run_id": run_id,
        "source_id": source_id,
        "source_label": source_label,
        "source_root_path": str(source_root),
        "dry_run": dry_run,
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": now.isoformat(),
        "counts": {
            "eligible_count": len(eligible),
            "deleted_count": len(deleted),
            "skipped_count": len(skipped),
            "total_bytes_eligible": int(sum(item["size_bytes"] for item in eligible)),
            "total_bytes_deleted": int(sum(item["size_bytes"] for item in deleted)),
        },
        "skipped_reasons": skipped_reason_counts,
        "skipped_samples": skipped_samples,
        "eligible_files": [item["relative_path"] for item in eligible],
        "deleted_files": [item["relative_path"] for item in deleted],
        "skipped_files": [
            {"relative_path": item.relative_path, "reason": item.reason}
            for item in skipped
        ],
        "preview": {
            "eligible_files": [item["relative_path"] for item in eligible[:REPORT_PREVIEW_LIMIT]],
            "deleted_files": [item["relative_path"] for item in deleted[:REPORT_PREVIEW_LIMIT]],
            "skipped_files": [
                {"relative_path": item.relative_path, "reason": item.reason}
                for item in skipped[:REPORT_PREVIEW_LIMIT]
            ],
        },
    }

    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(report_path)
