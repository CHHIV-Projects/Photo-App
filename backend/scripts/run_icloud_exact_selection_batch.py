"""Run one internal durable exact-selection iCloud acquisition batch.

This script is intentionally internal/non-UI. Real iCloud authentication and
download actions are operator-run, and all output is bounded, secret-free JSON.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import func, select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.asset import Asset  # noqa: E402
from app.models.icloud_acquisition_run import (  # noqa: E402
    IcloudAcquisitionBatch,
    IcloudAcquisitionResource,
    IcloudAcquisitionRun,
)
from app.models.ingestion_source import IngestionSource  # noqa: E402
from app.models.provenance import Provenance  # noqa: E402
from app.services.icloud_acquisition.durable_exact_service import (  # noqa: E402
    DurableExactAcquisitionError,
    get_source_intake_handoff_manifest,
    run_durable_exact_selection_batch,
)
from app.services.icloud_acquisition.exact_selection_adapter import (  # noqa: E402
    ExactSelectionHelperClient,
    ExactSelectionPrototypeError,
    count_partial_workspace_files,
    prepare_exact_selection_prototype,
    validate_exact_selection_profile,
)
from app.services.icloud_acquisition.phase0_validation import (  # noqa: E402
    CANDIDATE_ORDINARY_STILL,
    PHASE0_MAX_SCAN_LIMIT,
    build_phase0_list_summary,
)
from app.services.ingestion.pipeline_orchestrator import resolve_runtime_path  # noqa: E402


EXECUTION_CONFIRMATION = "EXECUTE_ICLOUD_EXACT_BATCH"
REPORT_TYPE = "icloud_exact_selection_batch_validation"
STOP_SELECTED_CANDIDATE_NOT_ORDINARY_STILL = "selected_candidate_not_ordinary_still"

_FORBIDDEN_OUTPUT_TERMS = (
    "password",
    "2fa",
    "two_factor",
    "cookie",
    "session",
    "token",
    "download_url",
    "remote_id",
    "item_id",
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Internal bounded exact-selection iCloud acquisition runner. "
            "Prints secret-free JSON only."
        )
    )
    parser.add_argument("--source-id", type=int, required=True)
    parser.add_argument("--target-new-items", type=int, default=1)
    parser.add_argument("--scan-limit", type=int, default=25)
    parser.add_argument(
        "--ordinary-still-only",
        action="store_true",
        default=True,
        help="Require exactly one ordinary still primary resource before execution.",
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--confirm",
        default="",
        help=f"Execution requires the exact value {EXECUTION_CONFIRMATION}.",
    )
    parser.add_argument("--created-by", default="internal_12_62_18")
    return parser


def _report_directory() -> Path:
    root = resolve_runtime_path("../storage/logs/icloud_exact_acquisition_reports")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _new_report_path(*, phase: str, source_id: int) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return _report_directory() / f"icloud_exact_acquisition_{phase}_{source_id}_{timestamp}.json"


def _assert_secret_free(payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, sort_keys=True, default=str).casefold()
    if any(term in serialized for term in _FORBIDDEN_OUTPUT_TERMS):
        raise RuntimeError("unsafe_secret_bearing_output")


def _write_report(payload: dict[str, Any], *, phase: str, source_id: int) -> str:
    report_path = _new_report_path(phase=phase, source_id=source_id)
    payload["report_path"] = str(report_path)
    _assert_secret_free(payload)
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return str(report_path)


def _database_counts(db_session) -> tuple[int, int]:
    asset_count = int(db_session.scalar(select(func.count()).select_from(Asset)) or 0)
    provenance_count = int(
        db_session.scalar(select(func.count()).select_from(Provenance)) or 0
    )
    return asset_count, provenance_count


def _safe_next_action(stop_reason: str | None, *, execution_safe: bool) -> str:
    if execution_safe:
        return "Run exact-selection acquisition"
    reason = (stop_reason or "").strip().lower()
    if reason == "staged_unknown_pending_intake":
        return "Run Source Intake first"
    if reason == "partial_workspace_present":
        return "Inspect or clear partial workspace"
    if reason in {
        "authentication_required",
        "auth_required",
        "session_expired",
        "reauthentication_required",
        "authentication_failed",
    }:
        return "Re-authenticate iCloud helper"
    if reason == "scan_limit_reached":
        return (
            "No unknown item found within the bounded scan limit; wait for a new "
            "ordinary still to sync or get approval for a larger internal scan limit"
        )
    if reason == STOP_SELECTED_CANDIDATE_NOT_ORDINARY_STILL:
        return "Pause for operator review; selected candidate is not an ordinary still"
    return "Stop and inspect report"


def _base_payload(
    *,
    phase: str,
    source_id: int,
    source_label: str | None,
    target_new_items: int,
    scan_limit: int,
    ordinary_still_only: bool,
) -> dict[str, Any]:
    return {
        "report_type": REPORT_TYPE,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "source_profile_id": source_id,
        "source_profile_label": source_label,
        "target_new_item_count": target_new_items,
        "candidate_scan_limit": scan_limit,
        "ordinary_still_only": bool(ordinary_still_only),
        "cloud_deletion_performed": False,
        "source_intake_performed": False,
        "vault_write_performed": False,
    }


def _validate_bounds(*, target_new_items: int, scan_limit: int) -> str | None:
    if target_new_items != 1:
        return "target_new_items_must_be_one_for_bounded_validation"
    if scan_limit < target_new_items or scan_limit > PHASE0_MAX_SCAN_LIMIT:
        return "invalid_candidate_scan_limit"
    return None


def build_dry_run_payload(
    db_session,
    *,
    source_id: int,
    target_new_items: int,
    scan_limit: int,
    ordinary_still_only: bool,
    helper_client: ExactSelectionHelperClient,
) -> dict[str, Any]:
    source = db_session.get(IngestionSource, source_id)
    source_label = source.source_label if source is not None else None
    payload = _base_payload(
        phase="dry_run",
        source_id=source_id,
        source_label=source_label,
        target_new_items=target_new_items,
        scan_limit=scan_limit,
        ordinary_still_only=ordinary_still_only,
    )
    bounds_error = _validate_bounds(target_new_items=target_new_items, scan_limit=scan_limit)
    if bounds_error is not None:
        payload.update(
            {
                "status": "blocked",
                "stop_reason": bounds_error,
                "next_safe_action": "Use target-new-items 1 and scan-limit 1-25",
                "execution_safe_to_attempt": False,
            }
        )
        return payload
    if source is None:
        payload.update(
            {
                "status": "failed",
                "stop_reason": "source_not_found",
                "next_safe_action": "Select a valid iCloud Source Profile",
                "execution_safe_to_attempt": False,
            }
        )
        return payload

    preparation = prepare_exact_selection_prototype(
        db_session,
        source_id=source_id,
        target_new_item_count=target_new_items,
        candidate_scan_limit=scan_limit,
        helper_client=helper_client,
    )
    summary = build_phase0_list_summary(preparation)
    execution_safe = bool(summary["execution_safe_to_attempt"])
    stop_reason = summary["stop_reason"]
    status = summary["status"]
    if (
        ordinary_still_only
        and summary["selected_candidate_kind"] != CANDIDATE_ORDINARY_STILL
        and summary["selected_logical_items"] > 0
    ):
        execution_safe = False
        status = "blocked"
        stop_reason = STOP_SELECTED_CANDIDATE_NOT_ORDINARY_STILL

    payload.update(
        {
            "status": status,
            "stop_reason": stop_reason,
            "auth_state": summary["auth_state"],
            "profile_validation_status": summary["profile_validation_status"],
            "logical_candidates_considered": summary["logical_candidates_considered"],
            "resource_candidates_considered": summary["resource_candidates_considered"],
            "known_logical_items": summary["known_logical_items"],
            "known_resources": summary["known_resources"],
            "unknown_logical_items": summary["unknown_logical_items"],
            "unknown_resources": summary["unknown_resources"],
            "selected_logical_items": summary["selected_logical_items"],
            "selected_resources": summary["selected_resources"],
            "selected_candidate_kind": summary["selected_candidate_kind"],
            "unsupported_or_blocked_count": (
                summary["unsupported_logical_items"] + summary["ambiguous_logical_items"]
            ),
            "staged_unknown_status": summary["staged_unknown_status"],
            "partial_workspace_status": summary["partial_workspace_status"],
            "execution_safe_to_attempt": execution_safe,
            "next_safe_action": _safe_next_action(stop_reason, execution_safe=execution_safe),
        }
    )
    return payload


def _resource_rows(db_session, *, batch_id: int | None) -> list[IcloudAcquisitionResource]:
    if batch_id is None:
        return []
    return list(
        db_session.scalars(
            select(IcloudAcquisitionResource)
            .join(IcloudAcquisitionResource.item)
            .where(IcloudAcquisitionResource.item.has(batch_id=batch_id))
            .order_by(IcloudAcquisitionResource.id)
        )
    )


def build_execute_payload(
    db_session,
    *,
    source_id: int,
    target_new_items: int,
    scan_limit: int,
    ordinary_still_only: bool,
    created_by: str,
    helper_client: ExactSelectionHelperClient,
) -> dict[str, Any]:
    source = db_session.get(IngestionSource, source_id)
    source_label = source.source_label if source is not None else None
    payload = _base_payload(
        phase="execute",
        source_id=source_id,
        source_label=source_label,
        target_new_items=target_new_items,
        scan_limit=scan_limit,
        ordinary_still_only=ordinary_still_only,
    )
    bounds_error = _validate_bounds(target_new_items=target_new_items, scan_limit=scan_limit)
    if bounds_error is not None:
        payload.update(
            {
                "status": "blocked",
                "stop_reason": bounds_error,
                "next_safe_action": "Use target-new-items 1 and scan-limit 1-25",
            }
        )
        return payload

    before_assets, before_provenance = _database_counts(db_session)
    result = run_durable_exact_selection_batch(
        db_session,
        source_id=source_id,
        target_new_item_count=target_new_items,
        candidate_scan_limit=scan_limit,
        helper_client=helper_client,
        created_by=created_by,
        ordinary_still_only=ordinary_still_only,
    )
    after_assets, after_provenance = _database_counts(db_session)

    run = db_session.get(IcloudAcquisitionRun, result.run_id)
    batch = db_session.get(IcloudAcquisitionBatch, result.batch_id) if result.batch_id else None
    resources = _resource_rows(db_session, batch_id=result.batch_id)
    profile = validate_exact_selection_profile(db_session, source_id=source_id)
    partial_status = "blocked" if count_partial_workspace_files(profile) else "clear"
    handoff_manifest = (
        get_source_intake_handoff_manifest(db_session, batch_id=batch.id)
        if batch is not None and result.batch_ready_for_source_intake
        else None
    )

    payload.update(
        {
            "run_id": result.run_id,
            "batch_id": result.batch_id,
            "status": result.status,
            "stop_reason": result.stop_reason,
            "next_safe_action": result.next_safe_action,
            "selected_logical_items": batch.selected_new_item_count if batch else 0,
            "selected_resources": batch.selected_new_resource_count if batch else 0,
            "downloaded_logical_items": batch.downloaded_item_count if batch else 0,
            "downloaded_resources": batch.downloaded_resource_count if batch else 0,
            "failed_logical_items": batch.failed_item_count if batch else 0,
            "failed_resources": batch.failed_resource_count if batch else 0,
            "batch_ready_for_source_intake": result.batch_ready_for_source_intake,
            "local_sha256_present": bool(resources)
            and all(bool(resource.local_sha256) for resource in resources),
            "post_execution_partial_workspace_status": partial_status,
            "asset_rows_changed": after_assets != before_assets,
            "provenance_rows_changed": after_provenance != before_provenance,
            "acquisition_run_status": run.status if run is not None else None,
            "acquisition_batch_status": batch.status if batch is not None else None,
            "ready_resource_count": (
                len(handoff_manifest["ready_resources"]) if handoff_manifest else 0
            ),
            "failed_or_deferred_count": (
                handoff_manifest["failed_or_deferred_count"] if handoff_manifest else None
            ),
        }
    )
    return payload


def main() -> int:
    args = _build_parser().parse_args()
    phase = "execute" if args.execute else "dry_run"
    try:
        if args.execute and args.confirm != EXECUTION_CONFIRMATION:
            payload = _base_payload(
                phase=phase,
                source_id=args.source_id,
                source_label=None,
                target_new_items=args.target_new_items,
                scan_limit=args.scan_limit,
                ordinary_still_only=args.ordinary_still_only,
            )
            payload.update(
                {
                    "status": "blocked",
                    "stop_reason": "execution_confirmation_required",
                    "next_safe_action": f"Re-run with --confirm {EXECUTION_CONFIRMATION}",
                }
            )
        elif args.dry_run and args.confirm:
            payload = _base_payload(
                phase=phase,
                source_id=args.source_id,
                source_label=None,
                target_new_items=args.target_new_items,
                scan_limit=args.scan_limit,
                ordinary_still_only=args.ordinary_still_only,
            )
            payload.update(
                {
                    "status": "blocked",
                    "stop_reason": "unexpected_confirmation_for_dry_run",
                    "next_safe_action": "Remove --confirm for dry-run planning",
                }
            )
        else:
            with SessionLocal() as db_session:
                if args.dry_run:
                    payload = build_dry_run_payload(
                        db_session,
                        source_id=args.source_id,
                        target_new_items=args.target_new_items,
                        scan_limit=args.scan_limit,
                        ordinary_still_only=args.ordinary_still_only,
                        helper_client=ExactSelectionHelperClient(),
                    )
                else:
                    payload = build_execute_payload(
                        db_session,
                        source_id=args.source_id,
                        target_new_items=args.target_new_items,
                        scan_limit=args.scan_limit,
                        ordinary_still_only=args.ordinary_still_only,
                        created_by=args.created_by,
                        helper_client=ExactSelectionHelperClient(),
                    )
                report_path = _write_report(
                    payload,
                    phase=phase,
                    source_id=args.source_id,
                )
                run_id = payload.get("run_id")
                if run_id:
                    run = db_session.get(IcloudAcquisitionRun, int(run_id))
                    if run is not None:
                        run.report_path = report_path
                        db_session.commit()
    except (DurableExactAcquisitionError, ExactSelectionPrototypeError) as exc:
        payload = _base_payload(
            phase=phase,
            source_id=args.source_id,
            source_label=None,
            target_new_items=args.target_new_items,
            scan_limit=args.scan_limit,
            ordinary_still_only=args.ordinary_still_only,
        )
        payload.update(
            {
                "status": "blocked",
                "stop_reason": getattr(exc, "code", "exact_selection_blocked"),
                "next_safe_action": "Stop and inspect report",
            }
        )
        _write_report(payload, phase=phase, source_id=args.source_id)
    except Exception:  # noqa: BLE001 - never print unbounded exception text here
        payload = _base_payload(
            phase=phase,
            source_id=args.source_id,
            source_label=None,
            target_new_items=args.target_new_items,
            scan_limit=args.scan_limit,
            ordinary_still_only=args.ordinary_still_only,
        )
        payload.update(
            {
                "status": "failed",
                "stop_reason": "unexpected_error",
                "next_safe_action": "Inspect backend logs before retrying",
            }
        )
        _write_report(payload, phase=phase, source_id=args.source_id)

    if "report_path" not in payload:
        _write_report(payload, phase=phase, source_id=args.source_id)
    _assert_secret_free(payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("status") == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
