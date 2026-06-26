"""Run the internal iCloud exact-selection multi-batch orchestration loop.

This is intentionally an internal/operator script. It does not add a normal UI
or Admin API surface, and it prints bounded, secret-free JSON.
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

from app.db.session import SessionLocal  # noqa: E402
from app.services.admin.icloud_staging_cleanup_execution_service import (  # noqa: E402
    EXECUTION_CONFIRMATION_PHRASE,
)
from app.services.icloud_acquisition.exact_selection_adapter import (  # noqa: E402
    ExactSelectionHelperClient,
    ExactSelectionPrototypeError,
)
from app.services.icloud_acquisition.internal_loop_orchestrator import (  # noqa: E402
    IcloudInternalLoopError,
    continue_internal_icloud_loop_cleanup,
    plan_internal_loop,
    start_internal_icloud_loop,
)
from app.services.ingestion.pipeline_orchestrator import resolve_runtime_path  # noqa: E402


REPORT_TYPE = "icloud_internal_multibatch_loop"
DEFAULT_BATCH_SIZE = 1
DEFAULT_TOTAL_LIMIT = 2
DEFAULT_CANDIDATE_SEARCH_CAP = 25
DEFAULT_CLEANUP_WAIT_TIMEOUT_SECONDS = 60.0

_FORBIDDEN_OUTPUT_TERMS = (
    "password",
    "2fa",
    "two_factor",
    "cookie",
    "session",
    "token",
    "download_url",
    "remote_id",
    "raw_remote",
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Internal bounded iCloud exact-selection orchestration runner. "
            "Coordinates acquire -> Source Intake -> guarded cleanup review."
        )
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true", help="Plan the first batch without downloading.")
    modes.add_argument(
        "--execute",
        action="store_true",
        help="Start a new orchestration and run until cleanup review or terminal stop.",
    )
    modes.add_argument(
        "--continue-cleanup",
        action="store_true",
        help="Execute a reviewed cleanup dry run, verify staging is clean, and continue if needed.",
    )
    parser.add_argument("--source-id", type=int)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--total-limit", type=int, default=DEFAULT_TOTAL_LIMIT)
    parser.add_argument(
        "--candidate-search-cap",
        dest="candidate_search_cap",
        type=int,
        default=None,
        help="Maximum total iCloud candidates to inspect while filling one batch.",
    )
    parser.add_argument(
        "--scan-limit",
        dest="candidate_search_cap",
        type=int,
        default=None,
        help=(
            "Backward-compatible alias for --candidate-search-cap. "
            "This is not batch size or total limit."
        ),
    )
    parser.add_argument(
        "--ordinary-still-only",
        action="store_true",
        default=True,
        help="Require each selected logical item to be one ordinary still primary resource.",
    )
    parser.add_argument(
        "--pause-before-cleanup",
        action="store_true",
        default=True,
        help="Pause after cleanup dry run for explicit operator cleanup approval.",
    )
    parser.add_argument("--orchestration-run-id", type=int)
    parser.add_argument("--cleanup-dry-run-id", type=int)
    parser.add_argument(
        "--confirm",
        default="",
        help=f"Cleanup continuation requires the exact value {EXECUTION_CONFIRMATION_PHRASE}.",
    )
    parser.add_argument("--created-by", default="internal_12_62_20")
    parser.add_argument(
        "--cleanup-wait-timeout-seconds",
        type=float,
        default=DEFAULT_CLEANUP_WAIT_TIMEOUT_SECONDS,
    )
    return parser


def _report_directory() -> Path:
    root = resolve_runtime_path("../storage/logs/icloud_internal_loop_reports")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _assert_secret_free(payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, sort_keys=True, default=str).casefold()
    if any(term in serialized for term in _FORBIDDEN_OUTPUT_TERMS):
        raise RuntimeError("unsafe_secret_bearing_output")


def _write_report(payload: dict[str, Any], *, phase: str, source_id: int | None) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    source_part = source_id if source_id is not None else "unknown"
    report_path = _report_directory() / f"icloud_internal_loop_{phase}_{source_part}_{timestamp}.json"
    payload["report_path"] = str(report_path)
    _assert_secret_free(payload)
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return str(report_path)


def _base_payload(*, phase: str, source_id: int | None) -> dict[str, Any]:
    return {
        "report_type": REPORT_TYPE,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "source_profile_id": source_id,
        "cloud_deletion_performed": False,
        "normal_ui_exposure_added": False,
        "normal_admin_api_exposure_added": False,
    }


def _continue_cleanup_command(*, orchestration_run_id: int, cleanup_dry_run_id: int) -> str:
    return "\n".join(
        (
            "$env:PYTHONPATH='backend'",
            "& '.\\.venv\\Scripts\\python.exe' '.\\backend\\scripts\\run_icloud_internal_loop.py' `",
            "  --continue-cleanup `",
            f"  --orchestration-run-id {orchestration_run_id} `",
            f"  --cleanup-dry-run-id {cleanup_dry_run_id} `",
            f"  --confirm '{EXECUTION_CONFIRMATION_PHRASE}'",
        )
    )


def _augment_operator_payload(
    payload: dict[str, Any],
    *,
    candidate_search_cap: int | None = None,
) -> dict[str, Any]:
    if candidate_search_cap is not None:
        payload.setdefault("candidate_search_cap", candidate_search_cap)
        payload.setdefault("scan_limit_meaning", "candidate_search_cap")
        payload.setdefault("candidate_scan_limit", candidate_search_cap)
    payload.setdefault("candidate_page_size", None)
    payload.setdefault("candidate_page_size_status", "deferred")
    payload.setdefault("candidate_pages_scanned", None)
    cleanup_dry_run_id = payload.get("cleanup_dry_run_id")
    orchestration_run_id = payload.get("orchestration_run_id")
    cleanup_review_required = (
        payload.get("status") == "paused_for_cleanup"
        and cleanup_dry_run_id is not None
        and orchestration_run_id is not None
    )
    payload["cleanup_review_required"] = cleanup_review_required
    if cleanup_review_required:
        payload["continue_cleanup_command"] = _continue_cleanup_command(
            orchestration_run_id=int(orchestration_run_id),
            cleanup_dry_run_id=int(cleanup_dry_run_id),
        )
    return payload


def build_dry_run_payload(
    db_session,
    *,
    source_id: int,
    batch_size: int,
    total_limit: int,
    candidate_search_cap: int,
    ordinary_still_only: bool,
    helper_client: ExactSelectionHelperClient,
) -> dict[str, Any]:
    payload = _base_payload(phase="dry_run", source_id=source_id)
    plan = plan_internal_loop(
        db_session,
        source_id=source_id,
        batch_size=batch_size,
        total_limit=total_limit,
        candidate_scan_limit=candidate_search_cap,
        ordinary_still_only=ordinary_still_only,
        helper_client=helper_client,
    )
    payload.update(plan)
    payload["source_intake_performed"] = False
    payload["cleanup_performed"] = False
    _augment_operator_payload(payload, candidate_search_cap=candidate_search_cap)
    _write_report(payload, phase="dry_run", source_id=source_id)
    return payload


def build_execute_payload(
    db_session,
    *,
    source_id: int,
    batch_size: int,
    total_limit: int,
    candidate_search_cap: int,
    ordinary_still_only: bool,
    pause_before_cleanup: bool,
    helper_client: ExactSelectionHelperClient,
    created_by: str,
    cleanup_wait_timeout_seconds: float,
) -> dict[str, Any]:
    result = start_internal_icloud_loop(
        db_session,
        source_id=source_id,
        batch_size=batch_size,
        total_limit=total_limit,
        candidate_scan_limit=candidate_search_cap,
        ordinary_still_only=ordinary_still_only,
        pause_before_cleanup=pause_before_cleanup,
        helper_client=helper_client,
        created_by=created_by,
        cleanup_wait_timeout_seconds=cleanup_wait_timeout_seconds,
    )
    payload = result.to_dict()
    payload["phase"] = "execute"
    payload["report_type"] = REPORT_TYPE
    payload["cloud_deletion_performed"] = False
    payload["normal_ui_exposure_added"] = False
    payload["normal_admin_api_exposure_added"] = False
    _augment_operator_payload(payload, candidate_search_cap=candidate_search_cap)
    _assert_secret_free(payload)
    return payload


def build_continue_cleanup_payload(
    db_session,
    *,
    orchestration_run_id: int,
    cleanup_dry_run_id: int,
    confirmation: str,
    helper_client: ExactSelectionHelperClient,
    cleanup_wait_timeout_seconds: float,
) -> dict[str, Any]:
    result = continue_internal_icloud_loop_cleanup(
        db_session,
        orchestration_run_id=orchestration_run_id,
        cleanup_dry_run_id=cleanup_dry_run_id,
        confirmation=confirmation,
        helper_client=helper_client,
        cleanup_wait_timeout_seconds=cleanup_wait_timeout_seconds,
    )
    payload = result.to_dict()
    payload["phase"] = "continue_cleanup"
    payload["report_type"] = REPORT_TYPE
    payload["cloud_deletion_performed"] = False
    payload["normal_ui_exposure_added"] = False
    payload["normal_admin_api_exposure_added"] = False
    _augment_operator_payload(payload)
    _assert_secret_free(payload)
    return payload


def _error_payload(*, phase: str, source_id: int | None, code: str, next_safe_action: str | None) -> dict[str, Any]:
    payload = _base_payload(phase=phase, source_id=source_id)
    payload.update(
        {
            "status": "blocked",
            "stop_reason": code,
            "failure_reason": None,
            "next_safe_action": next_safe_action or "Inspect orchestration report",
            "candidate_search_cap": None,
            "scan_limit_meaning": "candidate_search_cap",
            "candidate_page_size": None,
            "candidate_page_size_status": "deferred",
            "source_intake_performed": False,
            "cleanup_performed": False,
        }
    )
    try:
        _write_report(payload, phase=phase, source_id=source_id)
    except RuntimeError:
        payload.pop("report_path", None)
        payload["stop_reason"] = "unsafe_secret_bearing_output"
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    phase = "continue_cleanup" if args.continue_cleanup else ("execute" if args.execute else "dry_run")
    if args.continue_cleanup:
        if args.orchestration_run_id is None or args.cleanup_dry_run_id is None:
            parser.error("--continue-cleanup requires --orchestration-run-id and --cleanup-dry-run-id")
    elif args.source_id is None:
        parser.error("--dry-run and --execute require --source-id")
    candidate_search_cap = args.candidate_search_cap or DEFAULT_CANDIDATE_SEARCH_CAP

    try:
        with SessionLocal() as db_session:
            helper_client = ExactSelectionHelperClient()
            if args.dry_run:
                payload = build_dry_run_payload(
                    db_session,
                    source_id=args.source_id,
                    batch_size=args.batch_size,
                    total_limit=args.total_limit,
                    candidate_search_cap=candidate_search_cap,
                    ordinary_still_only=args.ordinary_still_only,
                    helper_client=helper_client,
                )
            elif args.execute:
                payload = build_execute_payload(
                    db_session,
                    source_id=args.source_id,
                    batch_size=args.batch_size,
                    total_limit=args.total_limit,
                    candidate_search_cap=candidate_search_cap,
                    ordinary_still_only=args.ordinary_still_only,
                    pause_before_cleanup=args.pause_before_cleanup,
                    helper_client=helper_client,
                    created_by=args.created_by,
                    cleanup_wait_timeout_seconds=args.cleanup_wait_timeout_seconds,
                )
            else:
                payload = build_continue_cleanup_payload(
                    db_session,
                    orchestration_run_id=args.orchestration_run_id,
                    cleanup_dry_run_id=args.cleanup_dry_run_id,
                    confirmation=args.confirm,
                    helper_client=helper_client,
                    cleanup_wait_timeout_seconds=args.cleanup_wait_timeout_seconds,
                )
    except IcloudInternalLoopError as exc:
        payload = _error_payload(
            phase=phase,
            source_id=args.source_id,
            code=exc.code,
            next_safe_action=exc.next_safe_action,
        )
    except ExactSelectionPrototypeError as exc:
        payload = _error_payload(
            phase=phase,
            source_id=args.source_id,
            code=exc.code,
            next_safe_action="Inspect orchestration report",
        )

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("status") in {"completed", "paused_for_cleanup"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
