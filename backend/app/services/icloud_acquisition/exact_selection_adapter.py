"""Backend-only prototype seam for exact selected iCloud acquisition.

This module is intentionally not registered as an API route or acquisition
mode. It validates one Source Profile, keeps remote IDs in memory, applies
durable profile-scoped known-state, and invokes the isolated helper through a
bounded secret-free JSON pipe.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ingestion_source import IngestionSource
from app.services.icloud_acquisition.exact_selection_protocol import (
    AUTHENTICATED,
    MAX_HELPER_JSON_BYTES,
    OPERATION_AUTH_STATUS,
    OPERATION_DOWNLOAD_SELECTED,
    OPERATION_LIST,
    PROTOCOL_VERSION,
    ExactSelectionProtocolError,
    decode_verification_checksum,
    normalize_relative_resource_path,
    validate_helper_request,
)
from app.services.icloud_acquisition.known_state_service import (
    CandidateKnownState,
    PreflightCandidate,
    evaluate_known_state,
)
from app.services.icloud_acquisition.new_count_planner import (
    MAX_CANDIDATE_SCAN_LIMIT,
    MAX_TARGET_NEW_ITEM_COUNT,
    PLAN_CLASSIFICATION_BLOCKED,
    STOP_STAGED_UNKNOWN_PENDING_INTAKE,
    ExplicitLogicalItemCandidate,
    ExplicitLogicalResourceCandidate,
    NewCountSelectionPlan,
    plan_explicit_new_count_selection,
)
from app.services.icloud_path_service import resolve_icloud_staging_path


BACKEND_ROOT = Path(__file__).resolve().parents[3]
PROJECT_ROOT = BACKEND_ROOT.parent
APPROVED_EXPORTS_ROOT = (PROJECT_ROOT / "storage" / "exports" / "icloud").resolve()
HELPER_SCRIPT = Path(__file__).with_name("icloud_exact_selection_helper.py").resolve()
DEFAULT_LIBRARY = "PrimarySync"
DEFAULT_HELPER_TIMEOUT_SECONDS = int(
    getattr(settings, "icloud_exact_helper_timeout_seconds", 7200)
)
_NON_BLOCKING_UNSUPPORTED_REASONS = frozenset({"unsupported_adjustment_metadata_only"})
_PRIMARY_ORIGINAL_RESOURCE_ID = "primary_original"
_STILL_EXTENSIONS = frozenset(
    {
        ".jpg",
        ".jpeg",
        ".heic",
        ".heif",
        ".png",
        ".tif",
        ".tiff",
        ".webp",
    }
)

PREPARATION_READY = "ready"
PREPARATION_BLOCKED = "blocked"
PREPARATION_FAILED = "failed"


class ExactSelectionPrototypeError(RuntimeError):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ExactSelectionProfileContext:
    source_id: int
    source_label: str
    account_username: str
    staging_root: Path


@dataclass(frozen=True)
class ExactSelectionResource:
    resource_id: str
    role: str
    relative_path: str
    expected_size: int
    expected_checksum: str
    content_type: str


@dataclass(frozen=True)
class ExactSelectionLogicalItem:
    item_id: str
    grouping: str
    identity_ambiguous: bool
    unsupported_reasons: tuple[str, ...]
    created_at: str
    added_at: str
    resources: tuple[ExactSelectionResource, ...]


@dataclass(frozen=True)
class ExactSelectionListing:
    source_exhausted: bool
    scan_limit_reached: bool
    logical_item_count: int
    resource_file_count: int
    ambiguous_item_count: int
    items: tuple[ExactSelectionLogicalItem, ...]


@dataclass(frozen=True)
class ExactSelectionPreparation:
    status: str
    stopping_reason: str
    guidance: str | None
    auth_state: str | None
    profile: ExactSelectionProfileContext
    listing: ExactSelectionListing | None
    plan: NewCountSelectionPlan | None
    download_request: dict[str, Any] | None
    staged_unknown_resource_count: int = 0
    error_code: str | None = None


def is_ordinary_still_logical_item(item: ExactSelectionLogicalItem) -> bool:
    """Return true when an iCloud logical item is safe for ordinary-still-only selection."""

    if item.identity_ambiguous or item.unsupported_reasons:
        return False
    if len(item.resources) != 1:
        return False
    resource = item.resources[0]
    if resource.resource_id != _PRIMARY_ORIGINAL_RESOURCE_ID:
        return False
    extension = Path(resource.relative_path).suffix.casefold()
    return resource.content_type.casefold().startswith("image/") or extension in _STILL_EXTENSIONS


def _contains_forbidden_helper_key(value: object) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized_key = str(key).replace("-", "_").casefold()
            contains_secret_term = any(
                term in normalized_key for term in ("password", "token", "cookie", "session")
            )
            contains_url = normalized_key == "url" or normalized_key.endswith("_url")
            if contains_secret_term or contains_url:
                return True
            if _contains_forbidden_helper_key(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_helper_key(item) for item in value)
    return False


def _resolve_helper_root() -> Path:
    configured = str(getattr(settings, "icloud_exact_helper_env_root", "") or "").strip()
    if configured:
        value = Path(configured).expanduser()
        return (value if value.is_absolute() else BACKEND_ROOT / value).resolve()
    return (PROJECT_ROOT / ".tools" / "icloud_exact_helper").resolve()


def resolve_exact_selection_helper_python() -> Path | None:
    helper_root = _resolve_helper_root()
    for candidate in (
        helper_root / "Scripts" / "python.exe",
        helper_root / "Scripts" / "python",
        helper_root / "bin" / "python3",
        helper_root / "bin" / "python",
    ):
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()
    return None


class ExactSelectionHelperClient:
    def __init__(
        self,
        *,
        helper_python: Path | None = None,
        helper_script: Path = HELPER_SCRIPT,
        timeout_seconds: int = DEFAULT_HELPER_TIMEOUT_SECONDS,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        heartbeat_callback: Callable[[], None] | None = None,
        stop_requested_callback: Callable[[], bool] | None = None,
        poll_interval_seconds: float = 1.0,
    ) -> None:
        self.helper_python = helper_python or resolve_exact_selection_helper_python()
        self.helper_script = helper_script.resolve()
        self.timeout_seconds = timeout_seconds
        self._runner = runner
        self.heartbeat_callback = heartbeat_callback
        self.stop_requested_callback = stop_requested_callback
        self.poll_interval_seconds = poll_interval_seconds

    def _invoke_with_polling(
        self,
        command: list[str],
        *,
        request_json: str,
    ) -> subprocess.CompletedProcess[str]:
        started = time.monotonic()
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stdout_file:
            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(BACKEND_ROOT),
                    stdin=subprocess.PIPE,
                    stdout=stdout_file,
                    stderr=subprocess.DEVNULL,
                    text=True,
                )
            except OSError as exc:
                raise ExactSelectionPrototypeError(
                    "The exact-selection helper could not start.",
                    code="helper_crash",
                ) from exc
            try:
                if process.stdin is None:
                    raise ExactSelectionPrototypeError(
                        "The exact-selection helper stdin pipe could not be opened.",
                        code="helper_crash",
                    )
                process.stdin.write(request_json)
                process.stdin.close()
                while process.poll() is None:
                    if self.heartbeat_callback is not None:
                        self.heartbeat_callback()
                    if (
                        self.stop_requested_callback is not None
                        and self.stop_requested_callback()
                    ):
                        process.terminate()
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=10)
                        raise ExactSelectionPrototypeError(
                            "The exact-selection helper was stopped.",
                            code="user_stopped",
                        )
                    if time.monotonic() - started > self.timeout_seconds:
                        process.kill()
                        process.wait(timeout=10)
                        raise ExactSelectionPrototypeError(
                            "The exact-selection helper timed out.",
                            code="helper_timeout",
                        )
                    time.sleep(max(0.1, self.poll_interval_seconds))
                if self.heartbeat_callback is not None:
                    self.heartbeat_callback()
                stdout_file.seek(0)
                stdout = stdout_file.read(MAX_HELPER_JSON_BYTES + 1)
                return subprocess.CompletedProcess(command, process.returncode, stdout=stdout)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)

    def invoke(self, request: dict[str, Any]) -> dict[str, Any]:
        validated_request = validate_helper_request(request)
        if self.helper_python is None or not self.helper_python.exists():
            raise ExactSelectionPrototypeError(
                "The isolated iCloud helper Python could not be resolved.",
                code="helper_unavailable",
            )
        if not self.helper_script.exists():
            raise ExactSelectionPrototypeError(
                "The exact-selection helper script could not be resolved.",
                code="helper_unavailable",
            )

        request_json = json.dumps(validated_request, separators=(",", ":"))
        if len(request_json.encode("utf-8")) > MAX_HELPER_JSON_BYTES:
            raise ExactSelectionPrototypeError(
                "The exact-selection helper request exceeded its bound.",
                code="helper_request_too_large",
            )
        command = [str(self.helper_python), str(self.helper_script)]
        if self._runner is subprocess.run:
            completed = self._invoke_with_polling(command, request_json=request_json)
        else:
            try:
                completed = self._runner(
                    command,
                    cwd=str(BACKEND_ROOT),
                    input=request_json,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    check=False,
                    timeout=self.timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                raise ExactSelectionPrototypeError(
                    "The exact-selection helper timed out.",
                    code="helper_timeout",
                ) from exc
            except OSError as exc:
                raise ExactSelectionPrototypeError(
                    "The exact-selection helper could not start.",
                    code="helper_crash",
                ) from exc

        stdout = completed.stdout or ""
        if len(stdout.encode("utf-8")) > MAX_HELPER_JSON_BYTES:
            raise ExactSelectionPrototypeError(
                "The exact-selection helper response exceeded its bound.",
                code="helper_response_too_large",
            )
        try:
            response = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise ExactSelectionPrototypeError(
                "The exact-selection helper returned invalid JSON.",
                code="helper_crash",
            ) from exc
        if not isinstance(response, dict):
            raise ExactSelectionPrototypeError(
                "The exact-selection helper returned an invalid response.",
                code="helper_crash",
            )
        if _contains_forbidden_helper_key(response):
            raise ExactSelectionPrototypeError(
                "The helper response violated the secret-free protocol.",
                code="helper_forbidden_output",
            )
        if response.get("protocol_version") != PROTOCOL_VERSION:
            raise ExactSelectionPrototypeError(
                "The helper protocol version did not match.",
                code="helper_protocol_mismatch",
            )
        if response.get("operation") != validated_request["operation"]:
            raise ExactSelectionPrototypeError(
                "The helper operation did not match.",
                code="helper_protocol_mismatch",
            )

        structured_download_result = (
            validated_request["operation"] == OPERATION_DOWNLOAD_SELECTED
            and "selected_new_item_count" in response
        )
        auth_status_result = validated_request["operation"] == OPERATION_AUTH_STATUS
        if response.get("status") == "failed" and not structured_download_result:
            code = str(response.get("error_code") or "helper_failed")[:128]
            raise ExactSelectionPrototypeError(
                "The helper reported a safe terminal failure.",
                code=code,
            )
        if completed.returncode != 0 and not structured_download_result and not auth_status_result:
            raise ExactSelectionPrototypeError(
                "The helper exited unsuccessfully.",
                code="helper_crash",
            )
        return response

    def check_auth(self, *, account_username: str) -> str:
        response = self.invoke(
            {
                "protocol_version": PROTOCOL_VERSION,
                "operation": OPERATION_AUTH_STATUS,
                "account_username": account_username,
            }
        )
        return _bounded_string(response.get("auth_state"), "auth_state", max_length=128)

    def list_candidates(
        self,
        *,
        account_username: str,
        candidate_scan_limit: int,
        library: str = DEFAULT_LIBRARY,
    ) -> ExactSelectionListing:
        response = self.invoke(
            {
                "protocol_version": PROTOCOL_VERSION,
                "operation": OPERATION_LIST,
                "account_username": account_username,
                "library": library,
                "candidate_scan_limit": candidate_scan_limit,
            }
        )
        return parse_listing_response(response, candidate_scan_limit=candidate_scan_limit)

    def download_selected(self, request: dict[str, Any]) -> dict[str, Any]:
        response = self.invoke(request)
        _validate_download_response(response, request)
        return response


def _bounded_string(value: object, field: str, *, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ExactSelectionPrototypeError(
            f"The helper returned an invalid {field}.",
            code="helper_invalid_response",
        )
    return value.strip()


def _validate_checksum(value: object) -> str:
    checksum = _bounded_string(value, "expected_checksum", max_length=256)
    try:
        decode_verification_checksum(checksum)
    except ExactSelectionProtocolError as exc:
        raise ExactSelectionPrototypeError(
            "The helper returned invalid verification metadata.",
            code="helper_invalid_response",
        ) from exc
    return checksum


def parse_listing_response(
    response: dict[str, Any],
    *,
    candidate_scan_limit: int,
) -> ExactSelectionListing:
    if response.get("operation") != OPERATION_LIST or response.get("status") != "completed":
        raise ExactSelectionPrototypeError(
            "The helper listing response was not successful.",
            code="helper_invalid_response",
        )
    if response.get("auth_state") != AUTHENTICATED:
        raise ExactSelectionPrototypeError(
            "The helper listing response was not authenticated.",
            code="authentication_required",
        )
    items_value = response.get("items")
    if not isinstance(items_value, list) or len(items_value) > candidate_scan_limit:
        raise ExactSelectionPrototypeError(
            "The helper returned an invalid candidate list.",
            code="helper_invalid_response",
        )

    items: list[ExactSelectionLogicalItem] = []
    raw_ambiguous_flags: list[bool] = []
    for item_value in items_value:
        if not isinstance(item_value, dict):
            raise ExactSelectionPrototypeError(
                "The helper returned an invalid logical item.",
                code="helper_invalid_response",
            )
        resources_value = item_value.get("resources")
        if not isinstance(resources_value, list) or len(resources_value) > 8:
            raise ExactSelectionPrototypeError(
                "The helper returned an invalid resource list.",
                code="helper_invalid_response",
            )
        resources: list[ExactSelectionResource] = []
        for resource_value in resources_value:
            if not isinstance(resource_value, dict):
                raise ExactSelectionPrototypeError(
                    "The helper returned an invalid resource.",
                    code="helper_invalid_response",
                )
            expected_size = resource_value.get("expected_size")
            if (
                not isinstance(expected_size, int)
                or isinstance(expected_size, bool)
                or expected_size < 0
            ):
                raise ExactSelectionPrototypeError(
                    "The helper returned an invalid resource size.",
                    code="helper_invalid_response",
                )
            resources.append(
                ExactSelectionResource(
                    resource_id=_bounded_string(
                        resource_value.get("resource_id"),
                        "resource_id",
                        max_length=128,
                    ),
                    role=_bounded_string(resource_value.get("role"), "role", max_length=128),
                    relative_path=normalize_relative_resource_path(
                        resource_value.get("relative_path")
                    ),
                    expected_size=expected_size,
                    expected_checksum=_validate_checksum(
                        resource_value.get("expected_checksum")
                    ),
                    content_type=_bounded_string(
                        resource_value.get("content_type"),
                        "content_type",
                        max_length=255,
                    ),
                )
            )
        unsupported = item_value.get("unsupported_reasons", [])
        if not isinstance(unsupported, list) or len(unsupported) > 20:
            raise ExactSelectionPrototypeError(
                "The helper returned invalid unsupported-reason data.",
                code="helper_invalid_response",
            )
        raw_unsupported_reasons = tuple(
            _bounded_string(reason, "unsupported_reason", max_length=128)
            for reason in unsupported
        )
        raw_identity_ambiguous = item_value.get("identity_ambiguous") is True or bool(
            raw_unsupported_reasons
        )
        raw_ambiguous_flags.append(raw_identity_ambiguous)
        unsupported_reasons = tuple(
            reason
            for reason in raw_unsupported_reasons
            if reason not in _NON_BLOCKING_UNSUPPORTED_REASONS
        )
        identity_ambiguous = bool(unsupported_reasons) or (
            item_value.get("identity_ambiguous") is True and not raw_unsupported_reasons
        )
        items.append(
            ExactSelectionLogicalItem(
                item_id=_bounded_string(item_value.get("item_id"), "item_id", max_length=512),
                grouping=_bounded_string(item_value.get("grouping"), "grouping", max_length=128),
                identity_ambiguous=identity_ambiguous,
                unsupported_reasons=unsupported_reasons,
                created_at=_bounded_string(
                    item_value.get("created_at"),
                    "created_at",
                    max_length=128,
                ),
                added_at=_bounded_string(
                    item_value.get("added_at"),
                    "added_at",
                    max_length=128,
                ),
                resources=tuple(resources),
            )
        )

    logical_item_count = response.get("logical_item_count")
    resource_file_count = response.get("resource_file_count")
    ambiguous_item_count = response.get("ambiguous_item_count")
    actual_resource_count = sum(len(item.resources) for item in items)
    actual_ambiguous_count = sum(1 for item in items if item.identity_ambiguous)
    raw_ambiguous_count = sum(1 for is_ambiguous in raw_ambiguous_flags if is_ambiguous)
    if (
        logical_item_count != len(items)
        or resource_file_count != actual_resource_count
        or ambiguous_item_count not in {actual_ambiguous_count, raw_ambiguous_count}
    ):
        raise ExactSelectionPrototypeError(
            "The helper listing counts did not match its candidate data.",
            code="helper_invalid_response",
        )
    source_exhausted = response.get("source_exhausted")
    scan_limit_reached = response.get("scan_limit_reached")
    if not isinstance(source_exhausted, bool) or not isinstance(scan_limit_reached, bool):
        raise ExactSelectionPrototypeError(
            "The helper returned invalid pagination state.",
            code="helper_invalid_response",
        )
    if source_exhausted == scan_limit_reached:
        raise ExactSelectionPrototypeError(
            "The helper returned contradictory pagination state.",
            code="helper_invalid_response",
        )
    return ExactSelectionListing(
        source_exhausted=source_exhausted,
        scan_limit_reached=scan_limit_reached,
        logical_item_count=len(items),
        resource_file_count=actual_resource_count,
        ambiguous_item_count=actual_ambiguous_count,
        items=tuple(items),
    )


def validate_exact_selection_profile(
    db_session: Session,
    *,
    source_id: int,
) -> ExactSelectionProfileContext:
    source = db_session.get(IngestionSource, source_id)
    if source is None:
        raise ExactSelectionPrototypeError("Source Profile not found.", code="source_not_found")
    if (source.profile_status or "").strip().lower() != "active":
        raise ExactSelectionPrototypeError(
            "Only an active Source Profile can be used.",
            code="profile_not_active",
        )
    if (source.source_type or "").strip().lower() != "cloud_export" or (
        source.cloud_provider or ""
    ).strip().lower() != "icloud":
        raise ExactSelectionPrototypeError(
            "The selected Source Profile is not an iCloud profile.",
            code="not_icloud_profile",
        )
    if (source.acquisition_method or "").strip().lower() != "icloudpd":
        raise ExactSelectionPrototypeError(
            "The selected Source Profile does not use icloudpd.",
            code="invalid_acquisition_method",
        )
    username = (source.account_username or "").strip()
    source_root_value = (source.source_root_path or "").strip()
    managed_root_value = (source.managed_staging_path or "").strip()
    if not username:
        raise ExactSelectionPrototypeError(
            "The selected Source Profile has no account username.",
            code="account_username_missing",
        )
    if not source_root_value or not managed_root_value:
        raise ExactSelectionPrototypeError(
            "The selected Source Profile has no managed staging path.",
            code="staging_path_missing",
        )

    source_root_input = Path(source_root_value).expanduser()
    managed_root_input = Path(managed_root_value).expanduser()
    if source_root_input.is_symlink() or managed_root_input.is_symlink():
        raise ExactSelectionPrototypeError(
            "The managed staging path cannot be a symbolic link.",
            code="unsafe_staging_path",
        )
    source_root = source_root_input.resolve()
    managed_root = managed_root_input.resolve()
    expected_root = resolve_icloud_staging_path(source.source_label).resolve()
    try:
        source_root.relative_to(APPROVED_EXPORTS_ROOT)
        managed_root.relative_to(APPROVED_EXPORTS_ROOT)
    except ValueError as exc:
        raise ExactSelectionPrototypeError(
            "The selected Source Profile staging path is outside the approved root.",
            code="unsafe_staging_path",
        ) from exc
    if source_root != managed_root or managed_root != expected_root:
        raise ExactSelectionPrototypeError(
            "Source root, managed staging, and canonical staging paths do not match.",
            code="staging_path_mismatch",
        )
    if not managed_root.exists() or not managed_root.is_dir():
        raise ExactSelectionPrototypeError(
            "The managed staging path is unavailable or unsafe.",
            code="staging_path_unavailable",
        )
    return ExactSelectionProfileContext(
        source_id=int(source.id),
        source_label=source.source_label,
        account_username=username,
        staging_root=managed_root,
    )


def _normal_staging_candidates(staging_root: Path) -> list[PreflightCandidate]:
    candidates: list[PreflightCandidate] = []
    for path in sorted(
        (path for path in staging_root.rglob("*") if path.is_file()),
        key=lambda value: str(value).casefold(),
    ):
        relative = path.relative_to(staging_root)
        if relative.parts and relative.parts[0].casefold() == ".partial":
            continue
        normalized = relative.as_posix()
        candidates.append(
            PreflightCandidate(
                raw_line=normalized,
                normalized_source_relative_path=normalized,
                unknown_identity=False,
            )
        )
    return candidates


def find_staged_unknown_resources(
    db_session: Session,
    *,
    profile: ExactSelectionProfileContext,
) -> tuple[CandidateKnownState, ...]:
    candidates = _normal_staging_candidates(profile.staging_root)
    if not candidates:
        return ()
    summary = evaluate_known_state(
        db_session,
        ingestion_source_id=profile.source_id,
        staging_root=profile.staging_root,
        candidates=candidates,
    )
    return tuple(
        candidate
        for candidate in summary.candidates
        if candidate.staged_known and not candidate.already_known
    )


def count_partial_workspace_files(profile: ExactSelectionProfileContext) -> int:
    partial_root = profile.staging_root / ".partial"
    if not partial_root.exists():
        return 0
    return sum(1 for path in partial_root.rglob("*") if path.is_file())


def build_plan_from_listing(
    db_session: Session,
    *,
    profile: ExactSelectionProfileContext,
    listing: ExactSelectionListing,
    target_new_item_count: int,
    candidate_scan_limit: int,
    ordinary_still_only: bool = False,
    skip_blocking_unsupported_relationships: bool = False,
) -> NewCountSelectionPlan:
    planning_items = (
        tuple(item for item in listing.items if is_ordinary_still_logical_item(item))
        if ordinary_still_only
        else listing.items
    )
    flat_candidates = [
        PreflightCandidate(
            raw_line=resource.relative_path,
            normalized_source_relative_path=resource.relative_path,
            unknown_identity=False,
        )
        for item in planning_items
        for resource in item.resources
    ]
    known_summary = evaluate_known_state(
        db_session,
        ingestion_source_id=profile.source_id,
        staging_root=profile.staging_root,
        candidates=flat_candidates,
    )

    explicit_items: list[ExplicitLogicalItemCandidate] = []
    offset = 0
    for item in planning_items:
        item_known_states = known_summary.candidates[offset : offset + len(item.resources)]
        offset += len(item.resources)
        explicit_items.append(
            ExplicitLogicalItemCandidate(
                adapter_logical_item_id=item.item_id,
                grouping=item.grouping,
                identity_ambiguous=(
                    item.identity_ambiguous
                    or any(
                        reason not in _NON_BLOCKING_UNSUPPORTED_REASONS
                        for reason in item.unsupported_reasons
                    )
                ),
                resources=tuple(
                    ExplicitLogicalResourceCandidate(
                        adapter_resource_id=resource.resource_id,
                        known_state=known_state,
                    )
                    for resource, known_state in zip(
                        item.resources,
                        item_known_states,
                        strict=True,
                    )
                ),
            )
        )
    return plan_explicit_new_count_selection(
        explicit_items,
        target_new_item_count=target_new_item_count,
        candidate_scan_limit=candidate_scan_limit,
        candidate_source_exhausted=listing.source_exhausted,
        block_on_ambiguous_identity=(
            ordinary_still_only or not skip_blocking_unsupported_relationships
        ),
    )


def build_exact_download_request(
    *,
    profile: ExactSelectionProfileContext,
    listing: ExactSelectionListing,
    plan: NewCountSelectionPlan,
    candidate_scan_limit: int,
    library: str = DEFAULT_LIBRARY,
    run_token: str | None = None,
) -> dict[str, Any] | None:
    if plan.classification == PLAN_CLASSIFICATION_BLOCKED:
        return None
    items_by_id = {item.item_id: item for item in listing.items}
    selected_items: list[dict[str, Any]] = []
    for planned_item in plan.items:
        if not planned_item.selected_new:
            continue
        item_id = planned_item.adapter_logical_item_id
        listed_item = items_by_id.get(item_id or "")
        if listed_item is None:
            raise ExactSelectionPrototypeError(
                "A planned logical item was missing from its listing.",
                code="selection_manifest_changed",
            )
        resources_by_id = {resource.resource_id: resource for resource in listed_item.resources}
        selected_resources: list[dict[str, Any]] = []
        for planned_resource in planned_item.resources:
            if not planned_resource.selected_for_download:
                continue
            resource = resources_by_id.get(planned_resource.adapter_resource_id or "")
            if resource is None:
                raise ExactSelectionPrototypeError(
                    "A planned resource was missing from its listing.",
                    code="selection_manifest_changed",
                )
            selected_resources.append(
                {
                    "resource_id": resource.resource_id,
                    "relative_path": resource.relative_path,
                    "expected_size": resource.expected_size,
                    "expected_checksum": resource.expected_checksum,
                }
            )
        if not selected_resources:
            raise ExactSelectionPrototypeError(
                "A selected new item had no unknown resources.",
                code="selection_manifest_invalid",
            )
        selected_items.append({"item_id": listed_item.item_id, "resources": selected_resources})
    if not selected_items:
        return None

    return validate_helper_request(
        {
            "protocol_version": PROTOCOL_VERSION,
            "operation": OPERATION_DOWNLOAD_SELECTED,
            "account_username": profile.account_username,
            "library": library,
            "candidate_scan_limit": candidate_scan_limit,
            "staging_root": str(profile.staging_root),
            "run_token": run_token or secrets.token_hex(16),
            "selected_items": selected_items,
        }
    )


def prepare_exact_selection_prototype(
    db_session: Session,
    *,
    source_id: int,
    target_new_item_count: int,
    candidate_scan_limit: int,
    helper_client: ExactSelectionHelperClient,
    library: str = DEFAULT_LIBRARY,
    ordinary_still_only: bool = False,
    skip_blocking_unsupported_relationships: bool = False,
) -> ExactSelectionPreparation:
    if target_new_item_count < 1 or target_new_item_count > MAX_TARGET_NEW_ITEM_COUNT:
        raise ExactSelectionPrototypeError(
            f"target_new_item_count must be between 1 and {MAX_TARGET_NEW_ITEM_COUNT}.",
            code="invalid_target_new_item_count",
        )
    if (
        candidate_scan_limit < target_new_item_count
        or candidate_scan_limit > MAX_CANDIDATE_SCAN_LIMIT
    ):
        raise ExactSelectionPrototypeError(
            "candidate_scan_limit must be bounded and at least the target count.",
            code="invalid_candidate_scan_limit",
        )

    profile = validate_exact_selection_profile(db_session, source_id=source_id)
    if count_partial_workspace_files(profile):
        return ExactSelectionPreparation(
            status=PREPARATION_FAILED,
            stopping_reason="partial_workspace_present",
            guidance="Resolve the prior exact-selection .partial workspace before retrying.",
            auth_state=None,
            profile=profile,
            listing=None,
            plan=None,
            download_request=None,
            error_code="partial_workspace_present",
        )
    staged_unknown = find_staged_unknown_resources(db_session, profile=profile)
    if staged_unknown:
        return ExactSelectionPreparation(
            status=PREPARATION_BLOCKED,
            stopping_reason=STOP_STAGED_UNKNOWN_PENDING_INTAKE,
            guidance="Run Source Intake first for staged unknown resources.",
            auth_state=None,
            profile=profile,
            listing=None,
            plan=None,
            download_request=None,
            staged_unknown_resource_count=len(staged_unknown),
        )

    try:
        auth_state = helper_client.check_auth(account_username=profile.account_username)
    except (ExactSelectionPrototypeError, ExactSelectionProtocolError) as exc:
        return ExactSelectionPreparation(
            status=PREPARATION_FAILED,
            stopping_reason="helper_unavailable",
            guidance="Inspect the isolated helper runtime and retry.",
            auth_state=None,
            profile=profile,
            listing=None,
            plan=None,
            download_request=None,
            error_code=getattr(exc, "code", "helper_unavailable"),
        )
    if auth_state != AUTHENTICATED:
        return ExactSelectionPreparation(
            status=PREPARATION_BLOCKED,
            stopping_reason=auth_state,
            guidance="Authenticate or re-authenticate with the isolated helper outside Photo Organizer.",
            auth_state=auth_state,
            profile=profile,
            listing=None,
            plan=None,
            download_request=None,
            error_code=auth_state,
        )

    try:
        listing = helper_client.list_candidates(
            account_username=profile.account_username,
            candidate_scan_limit=candidate_scan_limit,
            library=library,
        )
    except (ExactSelectionPrototypeError, ExactSelectionProtocolError) as exc:
        return ExactSelectionPreparation(
            status=PREPARATION_FAILED,
            stopping_reason="auth_or_acquisition_error",
            guidance="Inspect helper readiness, authentication, network, and Apple service state.",
            auth_state=auth_state,
            profile=profile,
            listing=None,
            plan=None,
            download_request=None,
            error_code=getattr(exc, "code", "helper_failed"),
        )

    plan = build_plan_from_listing(
        db_session,
        profile=profile,
        listing=listing,
        target_new_item_count=target_new_item_count,
        candidate_scan_limit=candidate_scan_limit,
        ordinary_still_only=ordinary_still_only,
        skip_blocking_unsupported_relationships=skip_blocking_unsupported_relationships,
    )
    request = build_exact_download_request(
        profile=profile,
        listing=listing,
        plan=plan,
        candidate_scan_limit=candidate_scan_limit,
        library=library,
    )
    status = (
        PREPARATION_BLOCKED
        if plan.classification == PLAN_CLASSIFICATION_BLOCKED
        else PREPARATION_READY
    )
    return ExactSelectionPreparation(
        status=status,
        stopping_reason=plan.stopping_reason,
        guidance=plan.guidance,
        auth_state=auth_state,
        profile=profile,
        listing=listing,
        plan=plan,
        download_request=request,
    )


def execute_prepared_exact_selection(
    db_session: Session,
    *,
    preparation: ExactSelectionPreparation,
    helper_client: ExactSelectionHelperClient,
) -> dict[str, Any]:
    if preparation.status != PREPARATION_READY or preparation.download_request is None:
        raise ExactSelectionPrototypeError(
            "The exact-selection prototype is not ready to execute.",
            code="preparation_not_ready",
        )
    current_profile = validate_exact_selection_profile(
        db_session,
        source_id=preparation.profile.source_id,
    )
    if current_profile != preparation.profile:
        raise ExactSelectionPrototypeError(
            "The selected Source Profile changed after planning.",
            code="source_profile_changed",
        )
    if count_partial_workspace_files(current_profile):
        raise ExactSelectionPrototypeError(
            "Resolve the prior exact-selection .partial workspace before retrying.",
            code="partial_workspace_present",
        )
    if find_staged_unknown_resources(db_session, profile=current_profile):
        raise ExactSelectionPrototypeError(
            "Run Source Intake first for staged unknown resources.",
            code="staged_unknown_pending_intake",
        )
    auth_state = helper_client.check_auth(account_username=current_profile.account_username)
    if auth_state != AUTHENTICATED:
        raise ExactSelectionPrototypeError(
            "The isolated helper is no longer authenticated.",
            code=auth_state,
        )
    return helper_client.download_selected(preparation.download_request)


def _validate_download_response(
    response: dict[str, Any],
    request: dict[str, Any],
) -> None:
    if response.get("operation") != OPERATION_DOWNLOAD_SELECTED:
        raise ExactSelectionPrototypeError(
            "The helper returned an invalid download response.",
            code="helper_invalid_response",
        )
    selected_items = request["selected_items"]
    selected_resource_count = sum(len(item["resources"]) for item in selected_items)
    fields = (
        "selected_new_item_count",
        "selected_new_resource_count",
        "downloaded_item_count",
        "downloaded_resource_count",
        "failed_item_count",
        "failed_resource_count",
    )
    if any(
        not isinstance(response.get(field), int) or isinstance(response.get(field), bool)
        for field in fields
    ):
        raise ExactSelectionPrototypeError(
            "The helper returned invalid download counts.",
            code="helper_invalid_response",
        )
    if response["selected_new_item_count"] != len(selected_items):
        raise ExactSelectionPrototypeError(
            "The helper logical-item count did not match the selection.",
            code="helper_invalid_response",
        )
    if response["selected_new_resource_count"] != selected_resource_count:
        raise ExactSelectionPrototypeError(
            "The helper resource count did not match the selection.",
            code="helper_invalid_response",
        )
    if (
        response["downloaded_item_count"] + response["failed_item_count"]
        != response["selected_new_item_count"]
        or response["downloaded_resource_count"] + response["failed_resource_count"]
        != response["selected_new_resource_count"]
    ):
        raise ExactSelectionPrototypeError(
            "The helper completion counts were inconsistent.",
            code="helper_invalid_response",
        )
