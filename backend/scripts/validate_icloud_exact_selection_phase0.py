"""User-operated bounded Phase 0 validation for iCloud exact selection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.services.icloud_acquisition.exact_selection_adapter import (  # noqa: E402
    ExactSelectionHelperClient,
    ExactSelectionPrototypeError,
)
from app.services.icloud_acquisition.phase0_validation import (  # noqa: E402
    PHASE_EXECUTE_ONE_STILL,
    PHASE_LIST_ONLY,
    PHASE_PRECHECK,
    Phase0ValidationError,
    build_phase0_failure_summary,
    execute_phase0_one_still,
    prepare_phase0_list_validation,
    resolve_phase0_source_profile,
    run_phase0_precheck,
)


EXECUTION_CONFIRMATION = "EXECUTE_ONE_ICLOUD_STILL"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run bounded, non-UI Phase 0 validation for the internal iCloud "
            "exact-selection helper."
        )
    )
    parser.add_argument("--source-label", required=True)
    parser.add_argument("--scan-limit", type=int, default=25)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--precheck-only", action="store_true")
    modes.add_argument("--list-only", action="store_true")
    modes.add_argument("--execute-one-still", action="store_true")
    parser.add_argument(
        "--confirm",
        default="",
        help=(
            "Execution mode requires the exact value "
            f"{EXECUTION_CONFIRMATION}."
        ),
    )
    return parser


def _phase(args: argparse.Namespace) -> str:
    if args.precheck_only:
        return PHASE_PRECHECK
    if args.list_only:
        return PHASE_LIST_ONLY
    return PHASE_EXECUTE_ONE_STILL


def main() -> int:
    args = _build_parser().parse_args()
    phase = _phase(args)
    source = None
    try:
        if args.execute_one_still and args.confirm != EXECUTION_CONFIRMATION:
            raise Phase0ValidationError("execution_not_safe")
        if not args.execute_one_still and args.confirm:
            raise Phase0ValidationError("execution_not_safe")

        with SessionLocal() as db_session:
            source = resolve_phase0_source_profile(
                db_session,
                source_label=args.source_label,
            )
            if args.precheck_only:
                summary = run_phase0_precheck(db_session, source=source)
            elif args.list_only:
                _, summary = prepare_phase0_list_validation(
                    db_session,
                    source=source,
                    candidate_scan_limit=args.scan_limit,
                    helper_client=ExactSelectionHelperClient(),
                )
            else:
                summary = execute_phase0_one_still(
                    db_session,
                    source=source,
                    candidate_scan_limit=args.scan_limit,
                    helper_client=ExactSelectionHelperClient(),
                )
    except (Phase0ValidationError, ExactSelectionPrototypeError) as exc:
        summary = build_phase0_failure_summary(
            phase=phase,
            source=source,
            error_code=getattr(exc, "code", "unknown_error"),
        )
    except Exception:  # noqa: BLE001 - never print exception text at this boundary
        summary = build_phase0_failure_summary(
            phase=phase,
            source=source,
            error_code="unknown_error",
        )

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
