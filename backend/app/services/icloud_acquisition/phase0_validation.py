"""Bounded, secret-free summaries for user-operated exact-selection validation.

This module is an internal validation seam. It does not register an API route,
acquisition mode, background job, Source Intake handoff, or cleanup action.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.ingestion_source import IngestionSource
from app.models.provenance import Provenance
from app.services.icloud_acquisition.exact_selection_adapter import (
    PREPARATION_BLOCKED,
    PREPARATION_FAILED,
    ExactSelectionHelperClient,
    ExactSelectionPreparation,
    count_partial_workspace_files,
    execute_prepared_exact_selection,
    find_staged_unknown_resources,
    prepare_exact_selection_prototype,
    validate_exact_selection_profile,
)
from app.services.icloud_acquisition.exact_selection_protocol import (
    AUTHENTICATED,
    AUTHENTICATION_FAILED,
    AUTHENTICATION_REQUIRED,
    HELPER_UNAVAILABLE,
    REAUTHENTICATION_REQUIRED,
    RESOURCE_LIVE_PHOTO_ORIGINAL,
    RESOURCE_PRIMARY_ORIGINAL,
    SESSION_EXPIRED,
    decode_verification_checksum,
)
from app.services.icloud_acquisition.new_count_planner import (
    STILL_EXTENSIONS,
    STOP_IDENTITY_UNAVAILABLE,
    STOP_LOGICAL_ITEM_IDENTITY_AMBIGUOUS,
    STOP_NO_MORE_CANDIDATES,
    STOP_SCAN_LIMIT_REACHED,
    STOP_STAGED_UNKNOWN_PENDING_INTAKE,
    STOP_TARGET_NEW_COUNT_REACHED,
    STOP_TOOLING_LIMIT_REACHED,
)


PHASE0_TARGET_NEW_ITEM_COUNT = 1
PHASE0_MAX_SCAN_LIMIT = 25

PHASE_PRECHECK = "precheck"
PHASE_LIST_ONLY = "list_only"
PHASE_EXECUTE_ONE_STILL = "execute_one_still"

CANDIDATE_NONE = "none"
CANDIDATE_ORDINARY_STILL = "ordinary_still_primary_only"
CANDIDATE_LIVE_PRIMARY_AND_MOTION = "live_photo_primary_and_motion"
CANDIDATE_LIVE_MOTION_ONLY = "live_photo_motion_only_known_primary"
CANDIDATE_LIVE_PRIMARY_ONLY = "live_photo_primary_only_known_motion"
CANDIDATE_NON_STILL_PRIMARY = "non_still_primary"
CANDIDATE_OTHER = "other_or_multiple"

_UNSUPPORTED_REASON_STOP_REASONS = {
    "unsupported_remote_sidecar": "unsupported_remote_sidecar",
    "unsupported_raw_or_alternative": "unsupported_raw_or_alternative",
    "unsupported_adjusted_resource": "unsupported_adjusted_resource",
    "identity_unavailable": "identity_unavailable",
    "verification_metadata_unavailable": "verification_metadata_unavailable",
    "identity_collision": "identity_collision",
}
_NON_BLOCKING_UNSUPPORTED_REASONS = frozenset({"unsupported_adjustment_metadata_only"})

STATUS_COMPLETED = "completed"
STATUS_BLOCKED = "blocked"
STATUS_FAILED = "failed"

_SAFE_AUTH_STATES = {
    AUTHENTICATED,
    AUTHENTICATION_REQUIRED,
    SESSION_EXPIRED,
    REAUTHENTICATION_REQUIRED,
    AUTHENTICATION_FAILED,
    HELPER_UNAVAILABLE,
    "not_checked",
    "unknown",
}

_SAFE_STOP_REASONS = {
    "precheck_passed",
    "source_not_found",
    "source_profile_ambiguous",
    "source_profile_changed",
    "profile_not_active",
    "not_icloud_profile",
    "invalid_acquisition_method",
    "account_username_missing",
    "staging_path_missing",
    "unsafe_staging_path",
    "staging_path_mismatch",
    "staging_path_unavailable",
    "partial_workspace_present",
    STOP_STAGED_UNKNOWN_PENDING_INTAKE,
    STOP_TARGET_NEW_COUNT_REACHED,
    STOP_NO_MORE_CANDIDATES,
    STOP_SCAN_LIMIT_REACHED,
    STOP_TOOLING_LIMIT_REACHED,
    STOP_IDENTITY_UNAVAILABLE,
    STOP_LOGICAL_ITEM_IDENTITY_AMBIGUOUS,
    AUTHENTICATION_REQUIRED,
    SESSION_EXPIRED,
    REAUTHENTICATION_REQUIRED,
    AUTHENTICATION_FAILED,
    HELPER_UNAVAILABLE,
    "helper_timeout",
    "helper_crash",
    "helper_protocol_mismatch",
    "helper_invalid_response",
    "helper_forbidden_output",
    "helper_request_too_large",
    "helper_response_too_large",
    "auth_or_acquisition_error",
    "network_error",
    "icloud_service_unavailable",
    "library_unavailable",
    "selected_candidate_not_ordinary_still",
    "execution_not_safe",
    "unsupported_remote_sidecar",
    "unsupported_raw_or_alternative",
    "unsupported_adjusted_resource",
    "unsupported_adjustment_metadata_only",
    "identity_unavailable",
    "verification_metadata_unavailable",
    "identity_collision",
    "multiple_unsupported_relationships",
    "invalid_scan_limit",
    "unsafe_summary_shape",
    "published_manifest_verification_failed",
    "partial_item_failed",
    "selected_item_not_found",
    "selection_manifest_changed",
    "resource_unavailable",
    "download_failed",
    "local_file_error",
    "size_mismatch",
    "checksum_mismatch",
    "destination_exists",
    "publish_failed",
    "publish_rollback_failed",
    "target_new_count_reached",
    "unknown_error",
}
_SAFE_DOWNLOAD_ITEM_FAILURE_REASONS = frozenset(
    {
        STOP_LOGICAL_ITEM_IDENTITY_AMBIGUOUS,
        "selected_item_not_found",
        "selection_manifest_changed",
        "resource_unavailable",
        "download_failed",
        "network_error",
        "local_file_error",
        "size_mismatch",
        "checksum_mismatch",
        "destination_exists",
        "publish_failed",
        "publish_rollback_failed",
        "unsafe_staging_path",
        "verification_metadata_unavailable",
    }
)

_SAFE_SUMMARY_KEYS = {
    "phase",
    "status",
    "auth_state",
    "source_profile_id",
    "source_profile_label",
    "profile_validation_status",
    "stop_reason",
    "logical_candidates_considered",
    "resource_candidates_considered",
    "known_logical_items",
    "known_resources",
    "unknown_logical_items",
    "unknown_resources",
    "selected_logical_items",
    "selected_resources",
    "unsupported_logical_items",
    "ambiguous_logical_items",
    "staged_unknown_status",
    "partial_workspace_status",
    "selected_candidate_kind",
    "known_primary_not_redownloaded",
    "unknown_motion_selected",
    "execution_safe_to_attempt",
    "downloaded_logical_items",
    "downloaded_resources",
    "failed_logical_items",
    "failed_resources",
    "published_manifest_verification",
    "post_execution_partial_workspace_status",
    "asset_rows_changed",
    "provenance_rows_changed",
    "source_intake_performed",
    "cleanup_performed",
    "cloud_deletion_performed",
    "vault_write_performed",
}

_FORBIDDEN_SUMMARY_KEY_TERMS = (
    "username",
    "password",
    "cookie",
    "token",
    "session",
    "remote_id",
    "item_id",
    "resource_id",
    "url",
    "path",
    "checksum",
    "salt",
    "digest",
)


class Phase0ValidationError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def normalize_phase0_scan_limit(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise Phase0ValidationError("invalid_scan_limit")
    if value < PHASE0_TARGET_NEW_ITEM_COUNT or value > PHASE0_MAX_SCAN_LIMIT:
        raise Phase0ValidationError("invalid_scan_limit")
    return value


def resolve_phase0_source_profile(
    db_session: Session,
    *,
    source_label: str,
) -> IngestionSource:
    cleaned_label = (source_label or "").strip()
    if not cleaned_label:
        raise Phase0ValidationError("source_not_found")
    rows = db_session.scalars(
        select(IngestionSource).where(
            func.lower(IngestionSource.source_label) == cleaned_label.casefold(),
            IngestionSource.source_type == "cloud_export",
            IngestionSource.cloud_provider == "icloud",
        )
    ).all()
    if not rows:
        raise Phase0ValidationError("source_not_found")
    if len(rows) != 1:
        raise Phase0ValidationError("source_profile_ambiguous")
    return rows[0]


def _safe_stop_reason(value: object) -> str:
    candidate = str(value or "unknown_error").strip().lower()
    return candidate if candidate in _SAFE_STOP_REASONS else "unknown_error"


def _safe_auth_state(value: object) -> str:
    candidate = str(value or "not_checked").strip().lower()
    return candidate if candidate in _SAFE_AUTH_STATES else "unknown"


def _base_summary(
    *,
    phase: str,
    source: IngestionSource | None,
) -> dict[str, Any]:
    return {
        "phase": phase,
        "status": STATUS_FAILED,
        "auth_state": "not_checked",
        "source_profile_id": int(source.id) if source is not None else None,
        "source_profile_label": source.source_label if source is not None else None,
        "profile_validation_status": "not_checked",
        "stop_reason": "unknown_error",
        "logical_candidates_considered": 0,
        "resource_candidates_considered": 0,
        "known_logical_items": 0,
        "known_resources": 0,
        "unknown_logical_items": 0,
        "unknown_resources": 0,
        "selected_logical_items": 0,
        "selected_resources": 0,
        "unsupported_logical_items": 0,
        "ambiguous_logical_items": 0,
        "staged_unknown_status": "not_checked",
        "partial_workspace_status": "not_checked",
        "selected_candidate_kind": CANDIDATE_NONE,
        "known_primary_not_redownloaded": False,
        "unknown_motion_selected": False,
        "execution_safe_to_attempt": False,
    }


def build_phase0_failure_summary(
    *,
    phase: str,
    source: IngestionSource | None,
    error_code: object,
) -> dict[str, Any]:
    summary = _base_summary(phase=phase, source=source)
    summary["stop_reason"] = _safe_stop_reason(error_code)
    return validate_phase0_summary(summary)


def run_phase0_precheck(
    db_session: Session,
    *,
    source: IngestionSource,
) -> dict[str, Any]:
    profile = validate_exact_selection_profile(db_session, source_id=int(source.id))
    partial_count = count_partial_workspace_files(profile)
    staged_unknown = find_staged_unknown_resources(db_session, profile=profile)
    summary = _base_summary(phase=PHASE_PRECHECK, source=source)
    summary["profile_validation_status"] = "passed"
    summary["staged_unknown_status"] = "blocked" if staged_unknown else "clear"
    summary["partial_workspace_status"] = "blocked" if partial_count else "clear"
    if partial_count:
        summary["status"] = STATUS_FAILED
        summary["stop_reason"] = "partial_workspace_present"
    elif staged_unknown:
        summary["status"] = STATUS_BLOCKED
        summary["stop_reason"] = STOP_STAGED_UNKNOWN_PENDING_INTAKE
    else:
        summary["status"] = STATUS_COMPLETED
        summary["stop_reason"] = "precheck_passed"
    return validate_phase0_summary(summary)


def _selected_candidate_shape(
    preparation: ExactSelectionPreparation,
) -> tuple[str, bool, bool]:
    plan = preparation.plan
    listing = preparation.listing
    if plan is None or listing is None:
        return CANDIDATE_NONE, False, False
    selected = [item for item in plan.items if item.selected_new]
    if len(selected) != 1:
        return (CANDIDATE_NONE if not selected else CANDIDATE_OTHER), False, False

    planned_item = selected[0]
    listed_item = next(
        (
            item
            for item in listing.items
            if item.item_id == planned_item.adapter_logical_item_id
        ),
        None,
    )
    if listed_item is None:
        return CANDIDATE_OTHER, False, False

    planned_by_resource_id = {
        resource.adapter_resource_id: resource for resource in planned_item.resources
    }
    listed_by_resource_id = {
        resource.resource_id: resource for resource in listed_item.resources
    }
    primary = planned_by_resource_id.get(RESOURCE_PRIMARY_ORIGINAL)
    motion = planned_by_resource_id.get(RESOURCE_LIVE_PHOTO_ORIGINAL)
    primary_selected = bool(primary and primary.selected_for_download)
    primary_known = bool(primary and primary.already_known)
    motion_selected = bool(motion and motion.selected_for_download)
    motion_known = bool(motion and motion.already_known)
    known_primary_not_redownloaded = primary_known and not primary_selected
    unknown_motion_selected = bool(motion and not motion.already_known and motion_selected)

    if motion is not None:
        if primary_selected and motion_selected:
            kind = CANDIDATE_LIVE_PRIMARY_AND_MOTION
        elif motion_selected and known_primary_not_redownloaded:
            kind = CANDIDATE_LIVE_MOTION_ONLY
        elif primary_selected and motion_known:
            kind = CANDIDATE_LIVE_PRIMARY_ONLY
        else:
            kind = CANDIDATE_OTHER
        return kind, known_primary_not_redownloaded, unknown_motion_selected

    listed_primary = listed_by_resource_id.get(RESOURCE_PRIMARY_ORIGINAL)
    primary_extension = (
        Path(listed_primary.relative_path).suffix.casefold()
        if listed_primary is not None
        else ""
    )
    if (
        primary_selected
        and listed_primary is not None
        and (
            listed_primary.content_type.casefold().startswith("image/")
            or primary_extension in STILL_EXTENSIONS
        )
    ):
        return CANDIDATE_ORDINARY_STILL, False, False
    if primary_selected:
        return CANDIDATE_NON_STILL_PRIMARY, False, False
    return CANDIDATE_OTHER, False, False


def _specific_unsupported_stop_reason(
    preparation: ExactSelectionPreparation,
) -> str | None:
    """Classify an unsupported listing without exposing provider values."""

    if preparation.stopping_reason != STOP_LOGICAL_ITEM_IDENTITY_AMBIGUOUS:
        return None
    listing = preparation.listing
    if listing is None:
        return None
    safe_reasons = {
        mapped
        for item in listing.items
        for reason in item.unsupported_reasons
        if reason not in _NON_BLOCKING_UNSUPPORTED_REASONS
        if (mapped := _UNSUPPORTED_REASON_STOP_REASONS.get(reason)) is not None
    }
    if len(safe_reasons) == 1:
        return next(iter(safe_reasons))
    if len(safe_reasons) > 1:
        return "multiple_unsupported_relationships"
    return None


def build_phase0_list_summary(
    preparation: ExactSelectionPreparation,
) -> dict[str, Any]:
    source = IngestionSource(
        id=preparation.profile.source_id,
        source_label=preparation.profile.source_label,
        source_label_normalized=preparation.profile.source_label.casefold(),
        source_type="cloud_export",
        source_root_path_normalized="",
    )
    summary = _base_summary(phase=PHASE_LIST_ONLY, source=source)
    summary["profile_validation_status"] = "passed"
    summary["auth_state"] = _safe_auth_state(preparation.auth_state)
    summary["stop_reason"] = _safe_stop_reason(
        preparation.error_code
        if preparation.status == PREPARATION_FAILED and preparation.error_code
        else preparation.stopping_reason
    )
    specific_unsupported_reason = _specific_unsupported_stop_reason(preparation)
    if specific_unsupported_reason is not None:
        summary["stop_reason"] = specific_unsupported_reason
    summary["status"] = (
        STATUS_FAILED
        if preparation.status == PREPARATION_FAILED
        else (STATUS_BLOCKED if preparation.status == PREPARATION_BLOCKED else STATUS_COMPLETED)
    )
    summary["staged_unknown_status"] = (
        "blocked" if preparation.staged_unknown_resource_count else "clear"
    )
    summary["partial_workspace_status"] = (
        "blocked"
        if preparation.stopping_reason == "partial_workspace_present"
        else "clear"
    )

    plan = preparation.plan
    listing = preparation.listing
    if plan is not None:
        all_resources = [resource for item in plan.items for resource in item.resources]
        summary.update(
            {
                "logical_candidates_considered": plan.candidate_scan_item_count,
                "resource_candidates_considered": plan.candidate_resource_count,
                "known_logical_items": sum(1 for item in plan.items if item.already_known),
                "known_resources": sum(
                    1 for resource in all_resources if resource.already_known
                ),
                "unknown_logical_items": sum(
                    1 for item in plan.items if not item.already_known
                ),
                "unknown_resources": sum(
                    1 for resource in all_resources if not resource.already_known
                ),
                "selected_logical_items": plan.selected_new_item_count,
                "selected_resources": plan.selected_new_resource_count,
                "ambiguous_logical_items": plan.ambiguous_item_count,
            }
        )
    if listing is not None:
        summary["unsupported_logical_items"] = sum(
            1
            for item in listing.items
            if any(
                reason not in _NON_BLOCKING_UNSUPPORTED_REASONS
                for reason in item.unsupported_reasons
            )
        )
        summary["ambiguous_logical_items"] = listing.ambiguous_item_count

    kind, known_primary, unknown_motion = _selected_candidate_shape(preparation)
    summary["selected_candidate_kind"] = kind
    summary["known_primary_not_redownloaded"] = known_primary
    summary["unknown_motion_selected"] = unknown_motion
    summary["execution_safe_to_attempt"] = bool(
        preparation.status not in {PREPARATION_BLOCKED, PREPARATION_FAILED}
        and preparation.download_request is not None
        and summary["auth_state"] == AUTHENTICATED
        and summary["stop_reason"] == STOP_TARGET_NEW_COUNT_REACHED
        and summary["selected_logical_items"] == 1
        and summary["selected_resources"] == 1
        and summary["unsupported_logical_items"] == 0
        and summary["ambiguous_logical_items"] == 0
        and summary["staged_unknown_status"] == "clear"
        and summary["partial_workspace_status"] == "clear"
        and kind == CANDIDATE_ORDINARY_STILL
    )
    return validate_phase0_summary(summary)


def prepare_phase0_list_validation(
    db_session: Session,
    *,
    source: IngestionSource,
    candidate_scan_limit: int,
    helper_client: ExactSelectionHelperClient,
) -> tuple[ExactSelectionPreparation, dict[str, Any]]:
    scan_limit = normalize_phase0_scan_limit(candidate_scan_limit)
    preparation = prepare_exact_selection_prototype(
        db_session,
        source_id=int(source.id),
        target_new_item_count=PHASE0_TARGET_NEW_ITEM_COUNT,
        candidate_scan_limit=scan_limit,
        helper_client=helper_client,
    )
    return preparation, build_phase0_list_summary(preparation)


def _database_counts(db_session: Session) -> tuple[int, int]:
    asset_count = int(db_session.scalar(select(func.count()).select_from(Asset)) or 0)
    provenance_count = int(
        db_session.scalar(select(func.count()).select_from(Provenance)) or 0
    )
    return asset_count, provenance_count


def _content_checksum_matches(path: Path, encoded_checksum: str) -> tuple[bool, bool]:
    try:
        algorithm, expected = decode_verification_checksum(encoded_checksum)
    except Exception:  # noqa: BLE001 - verification failure is terminal and secret-free
        return False, False
    if algorithm == "icloud_file_checksum":
        return True, False
    algorithms = {
        "md5": hashlib.md5,  # noqa: S324 - provider digest comparison only
        "sha1": hashlib.sha1,  # noqa: S324 - provider digest comparison only
        "sha256": hashlib.sha256,
    }
    factory = algorithms.get(algorithm)
    if factory is None:
        return False, False
    hasher = factory()
    try:
        with path.open("rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
                hasher.update(chunk)
    except OSError:
        return False, False
    return hasher.digest() == expected, True


def _verify_published_selection(preparation: ExactSelectionPreparation) -> tuple[bool, str]:
    request = preparation.download_request
    if request is None or len(request["selected_items"]) != 1:
        return False, "failed"
    content_digest_verified = True
    for resource in request["selected_items"][0]["resources"]:
        path = (preparation.profile.staging_root / resource["relative_path"]).resolve()
        try:
            path.relative_to(preparation.profile.staging_root.resolve())
        except ValueError:
            return False, "failed"
        try:
            if not path.is_file() or path.stat().st_size != resource["expected_size"]:
                return False, "failed"
        except OSError:
            return False, "failed"
        checksum_matches, digest_verified = _content_checksum_matches(
            path,
            resource["expected_checksum"],
        )
        if not checksum_matches:
            return False, "failed"
        content_digest_verified = content_digest_verified and digest_verified
    return True, ("passed" if content_digest_verified else "size_only_passed")


def _safe_download_item_failure_reason(response: dict[str, Any]) -> str | None:
    items = response.get("items")
    if not isinstance(items, list) or not items:
        return None
    failure_codes = {
        str(item.get("error_code", "")).strip().lower()
        for item in items
        if isinstance(item, dict) and item.get("status") == "failed"
    }
    failure_codes.discard("")
    safe_codes = {
        code for code in failure_codes if code in _SAFE_DOWNLOAD_ITEM_FAILURE_REASONS
    }
    if len(safe_codes) == 1 and len(failure_codes) == 1:
        return next(iter(safe_codes))
    return None


def execute_phase0_one_still(
    db_session: Session,
    *,
    source: IngestionSource,
    candidate_scan_limit: int,
    helper_client: ExactSelectionHelperClient,
) -> dict[str, Any]:
    preparation, list_summary = prepare_phase0_list_validation(
        db_session,
        source=source,
        candidate_scan_limit=candidate_scan_limit,
        helper_client=helper_client,
    )
    if not list_summary["execution_safe_to_attempt"]:
        list_summary["phase"] = PHASE_EXECUTE_ONE_STILL
        list_summary["status"] = STATUS_BLOCKED
        if list_summary["selected_candidate_kind"] != CANDIDATE_ORDINARY_STILL:
            list_summary["stop_reason"] = "selected_candidate_not_ordinary_still"
        else:
            list_summary["stop_reason"] = "execution_not_safe"
        return validate_phase0_summary(list_summary)

    before_assets, before_provenance = _database_counts(db_session)
    response = execute_prepared_exact_selection(
        db_session,
        preparation=preparation,
        helper_client=helper_client,
    )
    after_assets, after_provenance = _database_counts(db_session)
    published_verified, published_verification_status = _verify_published_selection(preparation)
    partial_count = count_partial_workspace_files(preparation.profile)

    response_completed = (
        response.get("status") == "completed"
        and response.get("downloaded_item_count") == 1
        and response.get("downloaded_resource_count") == 1
        and response.get("failed_item_count") == 0
        and response.get("failed_resource_count") == 0
    )
    asset_rows_changed = before_assets != after_assets
    provenance_rows_changed = before_provenance != after_provenance
    summary = dict(list_summary)
    summary.update(
        {
            "phase": PHASE_EXECUTE_ONE_STILL,
            "status": (
                STATUS_COMPLETED
                if response_completed
                and published_verified
                and partial_count == 0
                and not asset_rows_changed
                and not provenance_rows_changed
                else STATUS_FAILED
            ),
            "stop_reason": _safe_stop_reason(response.get("stop_reason")),
            "downloaded_logical_items": int(response.get("downloaded_item_count", 0)),
            "downloaded_resources": int(response.get("downloaded_resource_count", 0)),
            "failed_logical_items": int(response.get("failed_item_count", 0)),
            "failed_resources": int(response.get("failed_resource_count", 0)),
            "published_manifest_verification": published_verification_status,
            "post_execution_partial_workspace_status": (
                "clear" if partial_count == 0 else "blocked"
            ),
            "asset_rows_changed": asset_rows_changed,
            "provenance_rows_changed": provenance_rows_changed,
            "source_intake_performed": False,
            "cleanup_performed": False,
            "cloud_deletion_performed": False,
            "vault_write_performed": False,
        }
    )
    if not published_verified:
        summary["stop_reason"] = (
            _safe_download_item_failure_reason(response)
            or "published_manifest_verification_failed"
        )
    return validate_phase0_summary(summary)


def validate_phase0_summary(summary: dict[str, Any]) -> dict[str, Any]:
    unexpected = set(summary) - _SAFE_SUMMARY_KEYS
    if unexpected:
        raise Phase0ValidationError("unsafe_summary_shape")
    for key in summary:
        normalized = key.casefold()
        if any(term in normalized for term in _FORBIDDEN_SUMMARY_KEY_TERMS):
            raise Phase0ValidationError("unsafe_summary_shape")
    if summary.get("auth_state") not in _SAFE_AUTH_STATES:
        raise Phase0ValidationError("unsafe_summary_shape")
    if not re.fullmatch(r"[a-z0-9_]+", str(summary.get("stop_reason", ""))):
        raise Phase0ValidationError("unsafe_summary_shape")
    return summary
