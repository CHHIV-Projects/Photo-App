from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.icloud_acquisition_run import IcloudAcquisitionRun
from app.schemas.admin import (
    IcloudReadinessLastAcquisition,
    IcloudReadinessReason,
    IcloudSourceReadinessResponse,
)
from app.services.admin.ingestion_operation_guardrail_service import get_ingestion_operation_guardrail_snapshot
from app.services.admin.source_intake_service import get_source_profile_detail
from app.services.ingestion.ingestion_context_service import normalize_source_root_path

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_APPROVED_ICLOUD_EXPORTS_ROOT = (_PROJECT_ROOT / "storage" / "exports" / "icloud").resolve()
_AUTH_REQUIRED_CODES = {"AUTH_REQUIRED", "SESSION_EXPIRED"}


@dataclass(frozen=True)
class _ReasonMessages:
    PROFILE_NOT_ACTIVE: str = "Profile is not active. Mark it active before iCloud acquisition."
    NOT_ICLOUD_PROFILE: str = "This source profile is not an iCloud cloud-export profile."
    APPROVED_ROOT_BLOCKED: str = "Managed staging path is outside the approved iCloud exports root."
    PATH_MISMATCH: str = "Managed staging path does not match the expected iCloud acquisition path."
    SOURCE_ROOT_MISMATCH: str = "Source root path does not match the expected iCloud acquisition path."
    SOURCE_REGISTRATION_MISMATCH: str = "Source registration does not match iCloud acquisition launch requirements."
    SOURCE_REGISTRATION_UNKNOWN: str = "Source registration status is unknown because required identity data is incomplete."
    STAGING_FOLDER_MISSING: str = "Staging folder is missing but path is safe and can be created."
    AUTH_UNKNOWN: str = "iCloud authentication status is unknown."
    AUTH_REQUIRED: str = "iCloud authentication is required. Re-authenticate icloudpd outside Photo Organizer."
    SESSION_EXPIRED: str = "iCloud session expired. Re-authenticate icloudpd outside Photo Organizer."
    ICLOUD_ACQUISITION_ACTIVE: str = "Another iCloud acquisition run is currently active."
    SOURCE_INTAKE_ACTIVE: str = "A Source Intake run is currently active."
    ICLOUD_CLEANUP_ACTIVE: str = "An iCloud staging cleanup run is currently active."
    ACCOUNT_USERNAME_MISSING: str = "Account username is required for iCloud source profiles."
    MANAGED_STAGING_PATH_MISSING: str = "Managed staging path is required for iCloud source profiles."
    NO_RECENT_ACQUISITION: str = "No recent matching iCloud acquisition status was found."


_MESSAGES = _ReasonMessages()


def _normalize_path(path_value: str | None) -> str:
    return (path_value or "").strip().replace("\\", "/").replace("//", "/").lower()


def _paths_equivalent(path_a: str | None, path_b: str | None) -> bool:
    a = _normalize_path(path_a)
    b = _normalize_path(path_b)
    if not a or not b:
        return False
    return a == b or a.endswith(f"/{b}") or b.endswith(f"/{a}")


def _is_under_approved_root(path_value: str | None) -> bool | None:
    if not path_value:
        return None
    try:
        resolved = Path(path_value).expanduser().resolve()
        resolved.relative_to(_APPROVED_ICLOUD_EXPORTS_ROOT)
        return True
    except (ValueError, OSError):
        return False


def _resolve_latest_matching_acquisition(
    db_session: Session,
    *,
    source_label: str,
    source_type: str,
    expected_acquisition_path: str | None,
    managed_staging_path: str | None,
    source_root_path: str | None,
) -> IcloudAcquisitionRun | None:
    candidates = db_session.execute(
        select(IcloudAcquisitionRun)
        .where(
            IcloudAcquisitionRun.source_label == source_label,
            IcloudAcquisitionRun.source_type == source_type,
        )
        .order_by(IcloudAcquisitionRun.id.desc())
        .limit(50)
    ).scalars().all()

    for run in candidates:
        run_path = run.staging_path or run.source_root_path
        if _paths_equivalent(run_path, expected_acquisition_path):
            return run
        if _paths_equivalent(run_path, managed_staging_path):
            return run
        if _paths_equivalent(run_path, source_root_path):
            return run
    return None


def _reason(code: str, message: str) -> IcloudReadinessReason:
    return IcloudReadinessReason(code=code, message=message)


def _recommended_action(
    *,
    blocking_codes: set[str],
    warning_codes: set[str],
) -> str:
    if "NOT_ICLOUD_PROFILE" in blocking_codes:
        return "This profile is not iCloud. Use applicable local/external source intake workflows."
    if "PROFILE_NOT_ACTIVE" in blocking_codes:
        return "Mark the source profile active before using iCloud workflow."
    if "APPROVED_ROOT_BLOCKED" in blocking_codes:
        return "Resolve managed staging path to an approved iCloud exports root before acquisition."
    if "PATH_MISMATCH" in blocking_codes or "SOURCE_ROOT_MISMATCH" in blocking_codes:
        return "Resolve path alignment before acquisition. Creating a staging folder does not repair path alignment."
    if "SOURCE_REGISTRATION_MISMATCH" in blocking_codes:
        return "Align source registration identity (label/type/path) with expected iCloud acquisition path."
    if "AUTH_REQUIRED" in blocking_codes or "SESSION_EXPIRED" in blocking_codes:
        return "Re-authenticate icloudpd outside Photo Organizer, then refresh readiness."
    if {
        "ICLOUD_ACQUISITION_ACTIVE",
        "SOURCE_INTAKE_ACTIVE",
        "ICLOUD_CLEANUP_ACTIVE",
    } & blocking_codes:
        return "Wait for active ingestion-related operations to finish, then refresh readiness."
    if "STAGING_FOLDER_MISSING" in warning_codes:
        return "Verify or create the staging folder before acquisition."
    if "AUTH_UNKNOWN" in warning_codes:
        return "Authentication state is unknown. Confirm icloudpd session health outside the app, then refresh readiness."
    return "Profile appears ready for the future iCloud acquisition step."


def get_icloud_source_readiness(
    db_session: Session,
    *,
    source_id: int,
    include_username: bool = False,
) -> IcloudSourceReadinessResponse:
    detail = get_source_profile_detail(
        db_session,
        source_id=source_id,
        include_username=include_username,
    )

    is_icloud = detail.source_type == "cloud_export" and detail.cloud_provider == "icloud"
    blocking_reasons: list[IcloudReadinessReason] = []
    warnings: list[IcloudReadinessReason] = []

    def add_block(code: str, message: str) -> None:
        if all(existing.code != code for existing in blocking_reasons):
            blocking_reasons.append(_reason(code, message))

    def add_warning(code: str, message: str) -> None:
        if all(existing.code != code for existing in warnings):
            warnings.append(_reason(code, message))

    managed_staging_path = detail.managed_staging_path
    expected_path = detail.expected_acquisition_path
    source_root_path = detail.source_root_path

    approved_root_status: str = "unknown"
    staging_folder_status: str = "unknown"
    path_alignment_status: str = "unknown"
    source_root_alignment_status: str = "unknown"
    source_registration_status: str = "unknown"
    auth_status: str = "unknown"
    last_auth_error_code: str | None = None
    last_acquisition: IcloudReadinessLastAcquisition | None = None

    if not is_icloud:
        add_block("NOT_ICLOUD_PROFILE", _MESSAGES.NOT_ICLOUD_PROFILE)

    if detail.profile_status != "active":
        add_block("PROFILE_NOT_ACTIVE", _MESSAGES.PROFILE_NOT_ACTIVE)

    if is_icloud and not (detail.account_username_masked or "").strip() and not (detail.account_username or "").strip():
        add_block("ACCOUNT_USERNAME_MISSING", _MESSAGES.ACCOUNT_USERNAME_MISSING)

    if is_icloud and not managed_staging_path:
        add_block("MANAGED_STAGING_PATH_MISSING", _MESSAGES.MANAGED_STAGING_PATH_MISSING)

    approved_root_check = _is_under_approved_root(managed_staging_path)
    if approved_root_check is True:
        approved_root_status = "ok"
    elif approved_root_check is False:
        approved_root_status = "blocked"
        add_block("APPROVED_ROOT_BLOCKED", _MESSAGES.APPROVED_ROOT_BLOCKED)

    if managed_staging_path and expected_path:
        if _paths_equivalent(managed_staging_path, expected_path):
            path_alignment_status = "matched"
        else:
            path_alignment_status = "mismatch"
            add_block("PATH_MISMATCH", _MESSAGES.PATH_MISMATCH)

    if source_root_path and expected_path:
        if _paths_equivalent(source_root_path, expected_path):
            source_root_alignment_status = "matched"
        else:
            source_root_alignment_status = "mismatch"
            add_block("SOURCE_ROOT_MISMATCH", _MESSAGES.SOURCE_ROOT_MISMATCH)

    if managed_staging_path:
        if approved_root_status == "blocked":
            staging_folder_status = "unsafe"
        else:
            try:
                resolved = Path(managed_staging_path).expanduser().resolve()
                if resolved.exists() and resolved.is_dir():
                    staging_folder_status = "exists"
                else:
                    staging_folder_status = "missing"
                    add_warning("STAGING_FOLDER_MISSING", _MESSAGES.STAGING_FOLDER_MISSING)
            except OSError:
                staging_folder_status = "unknown"

    has_registration_identity = bool(
        is_icloud
        and detail.normalized_label
        and detail.source_type == "cloud_export"
        and source_root_path
        and expected_path
    )
    if has_registration_identity:
        if normalize_source_root_path(source_root_path) == normalize_source_root_path(expected_path):
            source_registration_status = "matched"
        else:
            source_registration_status = "mismatch"
            add_block("SOURCE_REGISTRATION_MISMATCH", _MESSAGES.SOURCE_REGISTRATION_MISMATCH)
    elif is_icloud:
        source_registration_status = "unknown"
        add_warning("SOURCE_REGISTRATION_UNKNOWN", _MESSAGES.SOURCE_REGISTRATION_UNKNOWN)

    matching_acquisition = None
    if is_icloud:
        matching_acquisition = _resolve_latest_matching_acquisition(
            db_session,
            source_label=detail.source_label,
            source_type=detail.source_type,
            expected_acquisition_path=expected_path,
            managed_staging_path=managed_staging_path,
            source_root_path=source_root_path,
        )

    if matching_acquisition is not None:
        last_acquisition = IcloudReadinessLastAcquisition(
            status=matching_acquisition.status,
            started_at=matching_acquisition.started_at,
            finished_at=matching_acquisition.completed_at,
            downloaded_count=int(matching_acquisition.downloaded_count or 0),
            skipped_count=int(matching_acquisition.skipped_existing_count or 0),
            failed_count=int(matching_acquisition.failed_count or 0),
            error_code=matching_acquisition.error_code,
            report_path=matching_acquisition.report_path,
        )
        if matching_acquisition.error_code in _AUTH_REQUIRED_CODES:
            auth_status = "action_required"
            last_auth_error_code = matching_acquisition.error_code
            add_block(matching_acquisition.error_code, _MESSAGES.AUTH_REQUIRED if matching_acquisition.error_code == "AUTH_REQUIRED" else _MESSAGES.SESSION_EXPIRED)
        else:
            auth_status = "unknown"
            add_warning("AUTH_UNKNOWN", _MESSAGES.AUTH_UNKNOWN)
    elif is_icloud:
        auth_status = "unknown"
        add_warning("AUTH_UNKNOWN", _MESSAGES.AUTH_UNKNOWN)

    guardrail_snapshot = get_ingestion_operation_guardrail_snapshot(db_session, source_id=source_id)
    conflicts = guardrail_snapshot.operation_conflicts

    for guardrail_reason in guardrail_snapshot.blocking_reasons:
        add_block(guardrail_reason.code, guardrail_reason.message)

    core_blocking_codes = {
        "PROFILE_NOT_ACTIVE",
        "NOT_ICLOUD_PROFILE",
        "APPROVED_ROOT_BLOCKED",
        "PATH_MISMATCH",
        "SOURCE_ROOT_MISMATCH",
        "SOURCE_REGISTRATION_MISMATCH",
        "ACCOUNT_USERNAME_MISSING",
        "MANAGED_STAGING_PATH_MISSING",
    }
    has_core_blockers = any(reason.code in core_blocking_codes for reason in blocking_reasons)
    if is_icloud and matching_acquisition is None and not has_core_blockers:
        add_warning("NO_RECENT_ACQUISITION", _MESSAGES.NO_RECENT_ACQUISITION)

    if blocking_reasons:
        readiness_status = "not_ready"
    elif warnings:
        readiness_status = "warning"
    else:
        readiness_status = "ready"

    recommended_action = _recommended_action(
        blocking_codes={reason.code for reason in blocking_reasons},
        warning_codes={reason.code for reason in warnings},
    )

    return IcloudSourceReadinessResponse(
        source_id=detail.source_id,
        is_icloud_profile=is_icloud,
        readiness_status=readiness_status,
        profile_status=detail.profile_status,
        source_label=detail.source_label,
        source_type=detail.source_type,
        cloud_provider=detail.cloud_provider,
        account_username_masked=detail.account_username_masked,
        source_root_path=detail.source_root_path,
        managed_staging_path=detail.managed_staging_path,
        expected_acquisition_path=detail.expected_acquisition_path,
        effective_path=detail.effective_path,
        approved_root_status=approved_root_status,
        staging_folder_status=staging_folder_status,
        path_alignment_status=path_alignment_status,
        source_root_alignment_status=source_root_alignment_status,
        source_registration_status=source_registration_status,
        auth_status=auth_status,
        last_auth_error_code=last_auth_error_code,
        operation_conflicts=conflicts,
        last_acquisition=last_acquisition,
        blocking_reasons=blocking_reasons,
        warnings=warnings,
        recommended_action=recommended_action,
    )