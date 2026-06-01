"""Service helpers for source intake admin visibility (12.24)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.icloud_acquisition_run import IcloudAcquisitionRun
from app.models.ingestion_run import IngestionRun
from app.models.ingestion_source import IngestionSource
from app.models.provenance import Provenance
from app.models.source_intake_run import SourceIntakeRun
from app.schemas.admin import (
    SourceProfileDetail,
    SourceProfileCreateRequest,
    SourceProfileCreateResponse,
    SourceProfilePathCheckResponse,
    SourceProfileStagingFolderCreateResponse,
    SourceProfileMetadataUpdateRequest,
    SourceProfileSummary,
    SourceIntakeReportCounts,
    SourceIntakeReportDetail,
    SourceIntakeReportSummary,
    SourceIntakeSourceSummary,
)
from app.services.ingestion.ingestion_context_schema import ensure_ingestion_context_schema
from app.services.ingestion.ingestion_context_service import (
    KNOWN_SOURCE_TYPES,
    normalize_source_label,
    normalize_source_root_path,
)

# Only filenames matching this pattern are served by the detail endpoint.
_SAFE_REPORT_FILENAME_RE = re.compile(r"^source_intake_[\w\-]+\.json$")
ALLOWED_PROFILE_STATUS = {"active", "inactive", "archived", "test", "deprecated", "all"}
ALLOWED_CLOUD_PROVIDERS = {"icloud", "onedrive", "google_photos", "dropbox", "other"}
ALLOWED_ACQUISITION_METHODS = {"icloudpd", "folder_scan", "manual_export", "none"}
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_APPROVED_ICLOUD_EXPORTS_ROOT = (_PROJECT_ROOT / "storage" / "exports" / "icloud").resolve()


def _mask_account_username(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if "@" in cleaned:
        local_part, domain = cleaned.split("@", 1)
        return f"{local_part[:1]}***@{domain}"
    if len(cleaned) <= 2:
        return "***"
    return f"{cleaned[:1]}***{cleaned[-1:]}"


def _normalize_profile_status(value: str | None) -> str:
    normalized_status = (value or "active").strip().lower()
    if normalized_status == "all" or normalized_status not in ALLOWED_PROFILE_STATUS:
        raise ValueError(
            "Invalid status filter. Allowed values: active, inactive, archived, test, deprecated."
        )
    return normalized_status


def _normalize_source_type_strict(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in KNOWN_SOURCE_TYPES:
        raise ValueError(
            "Invalid source_type. Allowed values: local_folder, external_drive, cloud_export, scan_batch, other."
        )
    return normalized


def _normalize_cloud_provider(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized not in ALLOWED_CLOUD_PROVIDERS:
        raise ValueError("Invalid cloud_provider. Allowed values: icloud, onedrive, google_photos, dropbox, other.")
    return normalized


def _normalize_acquisition_method(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized not in ALLOWED_ACQUISITION_METHODS:
        raise ValueError("Invalid acquisition_method. Allowed values: icloudpd, folder_scan, manual_export, none.")
    return normalized


def _to_absolute_path(path_value: str) -> str:
    raw = Path(path_value).expanduser()
    if raw.is_absolute():
        return str(raw.resolve())
    return str((_PROJECT_ROOT / raw).resolve())


def _to_project_relative_path(path_value: str | None) -> str | None:
    if not path_value:
        return None
    try:
        resolved = Path(path_value).resolve()
        relative = resolved.relative_to(_PROJECT_ROOT)
    except (ValueError, OSError):
        return None
    return relative.as_posix()


def _slugify_source_label(value: str) -> str:
    lowered = value.strip().lower()
    if not lowered:
        return "unnamed-source"
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "unnamed-source"


def _compute_managed_staging_path(source_label: str, cloud_provider: str) -> str:
    staging_path = (
        _PROJECT_ROOT
        / "storage"
        / "exports"
        / cloud_provider
        / _slugify_source_label(source_label)
    )
    return str(staging_path.resolve())


def _build_profile_reference_maps(
    db_session: Session,
    sources: list[IngestionSource],
) -> tuple[dict[int, int], dict[int, int], dict[int, int], dict[int, int]]:
    source_ids = [source.id for source in sources]
    if not source_ids:
        return {}, {}, {}, {}

    provenance_counts = {
        row.ingestion_source_id: row.count
        for row in db_session.execute(
            select(
                Provenance.ingestion_source_id,
                func.count(Provenance.id).label("count"),
            )
            .where(Provenance.ingestion_source_id.in_(source_ids))
            .group_by(Provenance.ingestion_source_id)
        ).all()
    }
    ingestion_runs_counts = {
        row.ingestion_source_id: row.count
        for row in db_session.execute(
            select(
                IngestionRun.ingestion_source_id,
                func.count(IngestionRun.id).label("count"),
            )
            .where(IngestionRun.ingestion_source_id.in_(source_ids))
            .group_by(IngestionRun.ingestion_source_id)
        ).all()
    }
    source_intake_runs_counts = {
        row.ingestion_source_id: row.count
        for row in db_session.execute(
            select(
                SourceIntakeRun.ingestion_source_id,
                func.count(SourceIntakeRun.id).label("count"),
            )
            .where(SourceIntakeRun.ingestion_source_id.in_(source_ids))
            .group_by(SourceIntakeRun.ingestion_source_id)
        ).all()
    }

    # iCloud runs do not currently carry ingestion_source_id; match via source identity fields.
    icloud_runs_counts: dict[int, int] = {}
    for source in sources:
        icloud_runs_counts[source.id] = db_session.scalar(
            select(func.count(IcloudAcquisitionRun.id)).where(
                IcloudAcquisitionRun.source_label == source.source_label,
                IcloudAcquisitionRun.source_type == source.source_type,
                IcloudAcquisitionRun.source_root_path == source.source_root_path,
            )
        ) or 0

    return (
        provenance_counts,
        ingestion_runs_counts,
        source_intake_runs_counts,
        icloud_runs_counts,
    )


def _to_source_profile_summary(
    source: IngestionSource,
    *,
    include_username: bool,
    last_run_at: datetime | None,
    provenance_count: int | None,
    ingestion_runs_count: int | None,
    source_intake_runs_count: int | None,
    icloud_acquisition_runs_count: int | None,
) -> SourceProfileSummary:
    return SourceProfileSummary(
        source_id=source.id,
        source_label=source.source_label,
        source_type=source.source_type,
        source_root_path=source.source_root_path,
        profile_status=source.profile_status,
        cloud_provider=source.cloud_provider,
        acquisition_method=source.acquisition_method,
        managed_staging_path=source.managed_staging_path,
        account_username_masked=_mask_account_username(source.account_username),
        account_username=source.account_username if include_username else None,
        first_seen_at=source.created_at,
        last_run_at=last_run_at,
        provenance_count=provenance_count,
        ingestion_runs_count=ingestion_runs_count,
        source_intake_runs_count=source_intake_runs_count,
        icloud_acquisition_runs_count=icloud_acquisition_runs_count,
    )


def _build_single_source_profile_summary(
    db_session: Session,
    source: IngestionSource,
    *,
    include_username: bool,
) -> SourceProfileSummary:
    latest_run_at = db_session.scalar(
        select(func.max(IngestionRun.created_at)).where(IngestionRun.ingestion_source_id == source.id)
    )
    (
        provenance_counts,
        ingestion_runs_counts,
        source_intake_runs_counts,
        icloud_runs_counts,
    ) = _build_profile_reference_maps(db_session, [source])

    return _to_source_profile_summary(
        source,
        include_username=include_username,
        last_run_at=latest_run_at,
        provenance_count=provenance_counts.get(source.id, 0),
        ingestion_runs_count=ingestion_runs_counts.get(source.id, 0),
        source_intake_runs_count=source_intake_runs_counts.get(source.id, 0),
        icloud_acquisition_runs_count=icloud_runs_counts.get(source.id, 0),
    )


def _is_referenced_summary(summary: SourceProfileSummary) -> bool:
    return any(
        (count or 0) > 0
        for count in (
            summary.provenance_count,
            summary.ingestion_runs_count,
            summary.source_intake_runs_count,
            summary.icloud_acquisition_runs_count,
        )
    )


def _resolve_effective_path(source: IngestionSource) -> tuple[str | None, str]:
    if source.source_type == "cloud_export" and source.cloud_provider == "icloud" and source.managed_staging_path:
        return source.managed_staging_path, "managed_staging_path"
    if source.source_root_path:
        return source.source_root_path, "source_root_path"
    if source.managed_staging_path:
        return source.managed_staging_path, "managed_staging_path"
    return None, "none"


def _build_profile_warnings(source: IngestionSource, summary: SourceProfileSummary) -> list[str]:
    warnings: list[str] = []
    if _is_referenced_summary(summary):
        warnings.append("This source profile has historical references. Edits should preserve provenance meaning.")
    if source.managed_staging_path and source.source_root_path and source.managed_staging_path != source.source_root_path:
        warnings.append(
            "Managed staging path differs from source root path. Existing source identity remains based on source root path."
        )
    return warnings


def _build_source_profile_detail(
    db_session: Session,
    source: IngestionSource,
    *,
    include_username: bool,
) -> SourceProfileDetail:
    summary = _build_single_source_profile_summary(
        db_session,
        source,
        include_username=include_username,
    )
    effective_path, effective_path_kind = _resolve_effective_path(source)
    warnings = _build_profile_warnings(source, summary)
    return SourceProfileDetail(
        **summary.model_dump(),
        normalized_label=source.source_label_normalized,
        effective_path=effective_path,
        effective_path_kind=effective_path_kind,
        source_root_path_relative=_to_project_relative_path(source.source_root_path),
        managed_staging_path_relative=_to_project_relative_path(source.managed_staging_path),
        effective_path_relative=_to_project_relative_path(effective_path),
        is_referenced=_is_referenced_summary(summary),
        has_path_divergence=bool(
            source.managed_staging_path
            and source.source_root_path
            and source.managed_staging_path != source.source_root_path
        ),
        warnings=warnings,
    )


def get_source_profile_detail(
    db_session: Session,
    *,
    source_id: int,
    include_username: bool = False,
) -> SourceProfileDetail:
    ensure_ingestion_context_schema(db_session)
    source = db_session.get(IngestionSource, source_id)
    if source is None:
        raise LookupError("Source profile not found.")
    return _build_source_profile_detail(
        db_session,
        source,
        include_username=include_username,
    )


def verify_source_profile_path(
    db_session: Session,
    *,
    source_id: int,
) -> SourceProfilePathCheckResponse:
    ensure_ingestion_context_schema(db_session)
    source = db_session.get(IngestionSource, source_id)
    if source is None:
        raise LookupError("Source profile not found.")

    path_value, path_kind = _resolve_effective_path(source)
    if path_kind == "none" or not path_value:
        raise ValueError("No path is configured for this source profile.")

    path_obj = Path(path_value)
    exists = path_obj.exists()
    return SourceProfilePathCheckResponse(
        source_id=source.id,
        path=path_value,
        path_relative=_to_project_relative_path(path_value),
        path_kind=path_kind,
        exists=exists,
        is_directory=path_obj.is_dir() if exists else False,
        checked_at=datetime.now(timezone.utc),
    )


def create_source_profile_staging_folder(
    db_session: Session,
    *,
    source_id: int,
) -> SourceProfileStagingFolderCreateResponse:
    ensure_ingestion_context_schema(db_session)
    source = db_session.get(IngestionSource, source_id)
    if source is None:
        raise LookupError("Source profile not found.")

    if source.source_type != "cloud_export" or source.cloud_provider != "icloud":
        raise ValueError("Create Staging Folder is only supported for iCloud source profiles.")
    if not source.managed_staging_path:
        raise ValueError("managed_staging_path is not configured for this source profile.")

    target_path = Path(source.managed_staging_path).resolve()
    try:
        target_path.relative_to(_APPROVED_ICLOUD_EXPORTS_ROOT)
    except ValueError as exc:
        raise ValueError("managed_staging_path is outside the approved iCloud exports root.") from exc

    if target_path.exists() and not target_path.is_dir():
        raise ValueError("managed_staging_path exists but is not a directory.")

    created = False
    if not target_path.exists():
        target_path.mkdir(parents=True, exist_ok=True)
        created = True

    return SourceProfileStagingFolderCreateResponse(
        source_id=source.id,
        path=str(target_path),
        path_relative=_to_project_relative_path(str(target_path)),
        created=created,
        exists=target_path.exists(),
        checked_at=datetime.now(timezone.utc),
    )


def _report_directory() -> Path:
    """Resolve the source intake reports directory relative to this file's location."""
    # backend/app/services/admin/ -> backend/
    backend_root = Path(__file__).resolve().parents[3]
    return (backend_root / "../storage/logs/source_intake_reports").resolve()


def _parse_report_counts(counts_dict: dict) -> SourceIntakeReportCounts:
    return SourceIntakeReportCounts(
        total_files_scanned=counts_dict.get("total_files_scanned"),
        skipped_already_known=counts_dict.get("skipped_already_known"),
        eligible_unknown_files=counts_dict.get("eligible_unknown_files"),
        selected_for_session=counts_dict.get("selected_for_session"),
        staged_to_dropzone=counts_dict.get("staged_to_dropzone"),
        processed_new_unique=counts_dict.get("processed_new_unique"),
        failed_or_rejected=counts_dict.get("failed_or_rejected"),
        deferred_unready_count=counts_dict.get("deferred_unready_count"),
        remaining_unknown_eligible=counts_dict.get("remaining_unknown_eligible"),
    )


def _parse_report_summary(report_path: Path) -> SourceIntakeReportSummary | None:
    """Parse one report file into a summary object. Returns None on malformed input."""
    try:
        data: dict = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None

    if not isinstance(data, dict):
        return None

    cfg = data.get("config") or {}
    raw_counts = data.get("counts") or {}
    counts = _parse_report_counts(raw_counts) if raw_counts else None

    return SourceIntakeReportSummary(
        report_filename=report_path.name,
        generated_at_utc=data.get("generated_at_utc"),
        source_label=data.get("source_label"),
        source_path=data.get("source_path"),
        ingestion_source_id=data.get("ingestion_source_id"),
        ingestion_run_id=data.get("ingestion_run_id"),
        ingest_source_limit=cfg.get("ingest_source_limit"),
        ingest_batch_size=cfg.get("ingest_batch_size"),
        source_complete=data.get("source_complete"),
        counts=counts,
    )


def list_recent_reports(limit: int = 50) -> list[SourceIntakeReportSummary]:
    """Scan report directory and return summaries sorted by generated_at desc."""
    report_dir = _report_directory()
    if not report_dir.exists():
        return []

    summaries: list[tuple[str, SourceIntakeReportSummary]] = []
    for report_path in report_dir.glob("source_intake_*.json"):
        summary = _parse_report_summary(report_path)
        if summary is None:
            continue
        sort_key = summary.generated_at_utc or ""
        summaries.append((sort_key, summary))

    summaries.sort(key=lambda pair: pair[0], reverse=True)
    return [s for _, s in summaries[:limit]]


def _build_report_index_by_run_id() -> dict[int, SourceIntakeReportSummary]:
    """Build a mapping of ingestion_run_id -> latest report summary."""
    report_dir = _report_directory()
    if not report_dir.exists():
        return {}

    index: dict[int, tuple[str, SourceIntakeReportSummary]] = {}
    for report_path in report_dir.glob("source_intake_*.json"):
        summary = _parse_report_summary(report_path)
        if summary is None or summary.ingestion_run_id is None:
            continue
        run_id = summary.ingestion_run_id
        sort_key = summary.generated_at_utc or ""
        existing = index.get(run_id)
        if existing is None or sort_key > existing[0]:
            index[run_id] = (sort_key, summary)

    return {run_id: s for run_id, (_, s) in index.items()}


def list_sources_with_latest_info(db_session: Session) -> list[SourceIntakeSourceSummary]:
    """
    Return known ingestion sources from DB, enriched with latest run timestamp
    and latest report counts where available.
    """
    ensure_ingestion_context_schema(db_session)

    # Query all sources
    sources = db_session.scalars(
        select(IngestionSource).order_by(IngestionSource.created_at.asc())
    ).all()

    if not sources:
        return []

    source_ids = [s.id for s in sources]

    # Latest ingestion_run per source
    latest_runs = db_session.execute(
        select(
            IngestionRun.ingestion_source_id,
            func.max(IngestionRun.id).label("latest_run_id"),
            func.max(IngestionRun.created_at).label("latest_run_at"),
        )
        .where(IngestionRun.ingestion_source_id.in_(source_ids))
        .group_by(IngestionRun.ingestion_source_id)
    ).all()

    latest_run_by_source: dict[int, tuple[int, datetime]] = {
        row.ingestion_source_id: (row.latest_run_id, row.latest_run_at)
        for row in latest_runs
    }

    # Build report index keyed by run_id
    report_index = _build_report_index_by_run_id()

    results: list[SourceIntakeSourceSummary] = []
    for source in sources:
        run_info = latest_run_by_source.get(source.id)
        latest_run_at: datetime | None = None
        latest_report: SourceIntakeReportSummary | None = None
        if run_info is not None:
            latest_run_id, latest_run_at = run_info
            latest_report = report_index.get(latest_run_id)

        results.append(
            SourceIntakeSourceSummary(
                source_id=source.id,
                source_label=source.source_label,
                source_type=source.source_type,
                source_root_path=source.source_root_path,
                account_username=source.account_username,
                first_seen_at=source.created_at,
                last_run_at=latest_run_at,
                latest_report_filename=latest_report.report_filename if latest_report else None,
                latest_counts=latest_report.counts if latest_report else None,
                source_complete=latest_report.source_complete if latest_report else None,
            )
        )

    # Sort most-recently-active first; sources with no runs go last.
    results.sort(
        key=lambda s: (
            s.last_run_at is None,
            -(s.last_run_at.timestamp() if s.last_run_at is not None else 0),
        )
    )
    return results


def list_source_profiles(
    db_session: Session,
    *,
    status: str = "active",
    include_username: bool = False,
) -> list[SourceProfileSummary]:
    """Return source profile summaries from ingestion_sources with status filtering."""
    ensure_ingestion_context_schema(db_session)

    normalized_status = (status or "active").strip().lower()
    if normalized_status not in ALLOWED_PROFILE_STATUS:
        raise ValueError(
            "Invalid status filter. Allowed values: active, inactive, archived, test, deprecated, all."
        )

    sources_stmt = select(IngestionSource).order_by(IngestionSource.created_at.asc())
    if normalized_status != "all":
        sources_stmt = sources_stmt.where(IngestionSource.profile_status == normalized_status)
    sources = db_session.scalars(sources_stmt).all()
    if not sources:
        return []

    source_ids = [s.id for s in sources]
    latest_runs = db_session.execute(
        select(
            IngestionRun.ingestion_source_id,
            func.max(IngestionRun.created_at).label("latest_run_at"),
        )
        .where(IngestionRun.ingestion_source_id.in_(source_ids))
        .group_by(IngestionRun.ingestion_source_id)
    ).all()
    latest_run_by_source: dict[int, datetime] = {
        row.ingestion_source_id: row.latest_run_at
        for row in latest_runs
    }
    (
        provenance_counts,
        ingestion_runs_counts,
        source_intake_runs_counts,
        icloud_runs_counts,
    ) = _build_profile_reference_maps(db_session, sources)

    results: list[SourceProfileSummary] = []
    for source in sources:
        results.append(
            _to_source_profile_summary(
                source,
                include_username=include_username,
                last_run_at=latest_run_by_source.get(source.id),
                provenance_count=provenance_counts.get(source.id, 0),
                ingestion_runs_count=ingestion_runs_counts.get(source.id, 0),
                source_intake_runs_count=source_intake_runs_counts.get(source.id, 0),
                icloud_acquisition_runs_count=icloud_runs_counts.get(source.id, 0),
            )
        )

    results.sort(
        key=lambda s: (
            s.last_run_at is None,
            -(s.last_run_at.timestamp() if s.last_run_at is not None else 0),
        )
    )
    return results


def update_source_profile_status(
    db_session: Session,
    *,
    source_id: int,
    profile_status: str,
    include_username: bool = False,
) -> SourceProfileSummary:
    """Update one source profile lifecycle status and return the updated summary."""
    ensure_ingestion_context_schema(db_session)
    normalized_status = _normalize_profile_status(profile_status)

    source = db_session.get(IngestionSource, source_id)
    if source is None:
        raise LookupError(f"Source profile {source_id} not found.")

    source.profile_status = normalized_status
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    return _build_single_source_profile_summary(
        db_session,
        source,
        include_username=include_username,
    )


def create_source_profile(
    db_session: Session,
    *,
    payload: SourceProfileCreateRequest,
    include_username: bool = False,
) -> SourceProfileCreateResponse:
    """Create or get a source profile with strict validation for Ingestion UI."""
    ensure_ingestion_context_schema(db_session)

    resolved_label = (payload.source_label or "").strip()
    if not resolved_label:
        raise ValueError("source_label is required.")

    resolved_type = _normalize_source_type_strict(payload.source_type)
    resolved_status = _normalize_profile_status(payload.profile_status)
    resolved_cloud_provider = _normalize_cloud_provider(payload.cloud_provider)
    resolved_acquisition_method = _normalize_acquisition_method(payload.acquisition_method)
    account_username = (payload.account_username or "").strip() or None

    root_path_input = (payload.source_root_path or "").strip()
    managed_staging_input = (payload.managed_staging_path or "").strip()

    if resolved_type == "cloud_export" and resolved_cloud_provider == "icloud":
        if not account_username:
            raise ValueError("account_username is required for iCloud source profiles.")
        if resolved_acquisition_method is None:
            resolved_acquisition_method = "icloudpd"
        managed_staging_path = managed_staging_input or _compute_managed_staging_path(
            resolved_label,
            resolved_cloud_provider,
        )
        effective_root_path = managed_staging_path
    else:
        managed_staging_path = managed_staging_input or None
        if resolved_type in {"local_folder", "external_drive", "cloud_export"} and not root_path_input:
            raise ValueError("source_root_path is required for this source_type.")
        effective_root_path = root_path_input or managed_staging_path

    if not effective_root_path:
        raise ValueError("Unable to determine effective source_root_path.")

    normalized_label = normalize_source_label(resolved_label)
    normalized_root = normalize_source_root_path(effective_root_path)

    existing = db_session.scalar(
        select(IngestionSource).where(
            IngestionSource.source_label_normalized == normalized_label,
            IngestionSource.source_type == resolved_type,
            IngestionSource.source_root_path_normalized == normalized_root,
        )
    )
    if existing is not None:
        return SourceProfileCreateResponse(
            already_exists=True,
            profile=_build_single_source_profile_summary(
                db_session,
                existing,
                include_username=include_username,
            ),
        )

    resolved_root = _to_absolute_path(effective_root_path)
    source = IngestionSource(
        source_label=resolved_label,
        source_label_normalized=normalized_label,
        source_type=resolved_type,
        source_root_path=resolved_root,
        source_root_path_normalized=normalized_root,
        profile_status=resolved_status,
        cloud_provider=resolved_cloud_provider,
        acquisition_method=resolved_acquisition_method,
        managed_staging_path=_to_absolute_path(managed_staging_path) if managed_staging_path else None,
        account_username=account_username,
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    return SourceProfileCreateResponse(
        already_exists=False,
        profile=_build_single_source_profile_summary(
            db_session,
            source,
            include_username=include_username,
        ),
    )


def update_source_profile_metadata(
    db_session: Session,
    *,
    source_id: int,
    payload: SourceProfileMetadataUpdateRequest,
    include_username: bool = False,
) -> SourceProfileSummary:
    """Update safe metadata fields for source profile edit UI."""
    ensure_ingestion_context_schema(db_session)
    source = db_session.get(IngestionSource, source_id)
    if source is None:
        raise LookupError("Source profile not found.")

    if payload.source_label is not None:
        new_label = payload.source_label.strip()
        if not new_label:
            raise ValueError("source_label cannot be empty.")
        source.source_label = new_label
        source.source_label_normalized = normalize_source_label(new_label)

    if payload.profile_status is not None:
        source.profile_status = _normalize_profile_status(payload.profile_status)

    if payload.cloud_provider is not None:
        source.cloud_provider = _normalize_cloud_provider(payload.cloud_provider)

    if payload.account_username is not None:
        source.account_username = payload.account_username.strip() or None

    resolved_cloud_provider = source.cloud_provider
    if payload.acquisition_method is not None:
        source.acquisition_method = _normalize_acquisition_method(payload.acquisition_method)

    if payload.cloud_provider is not None:
        resolved_cloud_provider = _normalize_cloud_provider(payload.cloud_provider)
        source.cloud_provider = resolved_cloud_provider

    if payload.managed_staging_path is not None:
        if source.source_type != "cloud_export":
            raise ValueError("managed_staging_path can only be edited for cloud_export source profiles.")
        if resolved_cloud_provider == "icloud":
            current_summary = _build_single_source_profile_summary(
                db_session,
                source,
                include_username=include_username,
            )
            if _is_referenced_summary(current_summary):
                raise ValueError("managed_staging_path cannot be edited for referenced iCloud source profiles.")
        cleaned_path = payload.managed_staging_path.strip()
        source.managed_staging_path = _to_absolute_path(cleaned_path) if cleaned_path else None

    # Source root path and source type remain locked in 12.61.4.
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    return _build_single_source_profile_summary(
        db_session,
        source,
        include_username=include_username,
    )


def get_report_detail(report_filename: str) -> SourceIntakeReportDetail | None:
    """
    Return full parsed JSON content of one report file.
    Returns None if the file does not exist or is malformed.
    Raises ValueError on unsafe filename.
    """
    if not _SAFE_REPORT_FILENAME_RE.match(report_filename):
        raise ValueError(f"Invalid report filename: {report_filename!r}")

    report_path = _report_directory() / report_filename

    # Confirm the resolved path is still within the report directory (traversal guard).
    report_dir = _report_directory()
    try:
        report_path.resolve().relative_to(report_dir.resolve())
    except ValueError:
        raise ValueError(f"Invalid report filename: {report_filename!r}") from None

    if not report_path.exists():
        return None

    try:
        data: dict = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None

    if not isinstance(data, dict):
        return None

    # Truncate large lists to keep response size reasonable
    if isinstance(data.get("selected_files"), list) and len(data["selected_files"]) > 25:
        data["selected_files"] = data["selected_files"][:25]
        data["_selected_files_truncated"] = True

    return SourceIntakeReportDetail(report_filename=report_filename, raw=data)
