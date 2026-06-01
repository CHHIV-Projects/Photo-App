"""Service helpers for source intake admin visibility (12.24)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ingestion_run import IngestionRun
from app.models.ingestion_source import IngestionSource
from app.schemas.admin import (
    SourceProfileSummary,
    SourceIntakeReportCounts,
    SourceIntakeReportDetail,
    SourceIntakeReportSummary,
    SourceIntakeSourceSummary,
)
from app.services.ingestion.ingestion_context_schema import ensure_ingestion_context_schema

# Only filenames matching this pattern are served by the detail endpoint.
_SAFE_REPORT_FILENAME_RE = re.compile(r"^source_intake_[\w\-]+\.json$")
ALLOWED_PROFILE_STATUS = {"active", "inactive", "archived", "test", "deprecated", "all"}


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

    results: list[SourceProfileSummary] = []
    for source in sources:
        results.append(
            SourceProfileSummary(
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
                last_run_at=latest_run_by_source.get(source.id),
            )
        )

    results.sort(
        key=lambda s: (
            s.last_run_at is None,
            -(s.last_run_at.timestamp() if s.last_run_at is not None else 0),
        )
    )
    return results


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
