"""Bounded durable operations bridging Linux authority to the outbound Windows Helper."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import ntpath
from pathlib import PureWindowsPath
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ingestion_source import IngestionSource
from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointObservedPath
from app.models.windows_helper import WindowsHelperCredential, WindowsHelperOperation
from app.schemas.windows_helper import (
    CreateWindowsHelperInventoryOperationRequest,
    CreateWindowsHelperProbeOperationRequest,
    WindowsHelperOperationCreatedResponse,
    WindowsHelperOperationStatusResponse,
    WindowsInventoryCandidate,
)
from app.services.windows_helper.service import (
    HELPER_PROVIDER_NAME,
    WindowsHelperServiceError,
)
from app.windows_helper_shared.channel import (
    ClaimedInventoryOperation,
    ClaimedProbeOperation,
    HelperOperationClaimResponse,
    HelperOperationCompletionResponse,
    HelperOperationFailureRequest,
    HelperOperationFailureResponse,
)
from app.windows_helper_shared.protocol import (
    ErrorCode,
    HelperInventoryPageRequest,
    HelperInventoryPageResponse,
    HelperProbeRequest,
    HelperProbeResponse,
    InventoryResultStatus,
    MAX_INVENTORY_RESULT_BYTES,
    ProviderNativePath,
    canonical_protocol_digest,
)


UNCLAIMED_OPERATION_TTL = timedelta(minutes=10)
CLAIM_LEASE = timedelta(minutes=6)
COMPLETED_PROBE_FRESHNESS = timedelta(minutes=5)
HELPER_OFFLINE_AFTER = timedelta(seconds=90)
HELPER_POLL_SECONDS = 2
EXPECTED_COLLECTOR_NAME = "windows_non_admin_probe_v1"
EXPECTED_COLLECTOR_VERSION = "1"
_TERMINAL_STATES = {"completed", "failed", "expired"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _json(model: object) -> str:
    return json.dumps(
        model.model_dump(mode="json", exclude_none=True),  # type: ignore[attr-defined]
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _load_access_node(db: Session, access_node_id: UUID) -> AccessNode:
    node = db.scalar(select(AccessNode).where(AccessNode.access_node_uuid == str(access_node_id)))
    if (
        node is None
        or node.provider_name != HELPER_PROVIDER_NAME
        or node.os_family != "windows"
        or node.status != "active"
    ):
        raise WindowsHelperServiceError(
            "access_node_unavailable",
            "The requested Windows Helper Access Node is unavailable.",
            http_status=409,
        )
    credential = db.scalar(
        select(WindowsHelperCredential).where(
            WindowsHelperCredential.access_node_id == node.id,
            WindowsHelperCredential.status == "active",
            WindowsHelperCredential.revoked_at.is_(None),
        )
    )
    if credential is None:
        raise WindowsHelperServiceError(
            "helper_credential_unavailable",
            "The requested Windows Helper credential is unavailable.",
            http_status=409,
        )
    return node


def windows_helper_profile_binding(
    db: Session,
    source_profile_id: int,
    access_node: AccessNode | None = None,
) -> tuple[IngestionSource, SourceEndpoint, AccessNode]:
    """Return the one exact Helper Access Node authorized for a saved Profile."""
    return _profile_binding(db, source_profile_id, access_node)


def is_windows_helper_profile(
    db: Session,
    source: IngestionSource,
    endpoint: SourceEndpoint,
) -> bool:
    """Recognize Helper ownership even when an existing Endpoint was reused."""
    created_node = endpoint.created_from_access_node
    if created_node is not None and created_node.provider_name == HELPER_PROVIDER_NAME:
        return True
    observed_path_id = db.scalar(
        select(SourceEndpointObservedPath.id)
        .join(AccessNode, SourceEndpointObservedPath.access_node_id == AccessNode.id)
        .where(
            SourceEndpointObservedPath.source_endpoint_id == endpoint.id,
            AccessNode.provider_name == HELPER_PROVIDER_NAME,
        )
        .limit(1)
    )
    return observed_path_id is not None


def _profile_binding(
    db: Session,
    source_profile_id: int,
    access_node: AccessNode | None = None,
) -> tuple[IngestionSource, SourceEndpoint, AccessNode]:
    source = db.get(IngestionSource, source_profile_id)
    if source is None or source.profile_status != "active" or source.endpoint_id is None:
        raise WindowsHelperServiceError(
            "source_profile_unavailable",
            "The requested Source Profile is unavailable.",
            http_status=404,
        )
    endpoint = db.get(SourceEndpoint, source.endpoint_id)
    if endpoint is None or endpoint.status == "retired":
        raise WindowsHelperServiceError(
            "source_endpoint_unavailable",
            "The requested Source Endpoint is unavailable.",
            http_status=409,
        )
    statement = (
        select(AccessNode)
        .join(SourceEndpointObservedPath, SourceEndpointObservedPath.access_node_id == AccessNode.id)
        .where(
            SourceEndpointObservedPath.source_endpoint_id == endpoint.id,
            AccessNode.provider_name == HELPER_PROVIDER_NAME,
            AccessNode.os_family == "windows",
            AccessNode.status == "active",
        )
        .distinct()
    )
    if access_node is not None:
        statement = statement.where(AccessNode.id == access_node.id)
    nodes = list(db.scalars(statement))
    if len(nodes) != 1:
        raise WindowsHelperServiceError(
            "source_access_node_ambiguous",
            "The Source Profile does not have one exact Windows Helper Access Node.",
            http_status=409,
        )
    _load_access_node(db, UUID(nodes[0].access_node_uuid))
    return source, endpoint, nodes[0]


def _create_operation(
    db: Session,
    *,
    operation_id: UUID,
    access_node: AccessNode,
    operation_type: str,
    request: HelperProbeRequest | HelperInventoryPageRequest,
    source_endpoint_id: int | None = None,
    source_profile_id: int | None = None,
) -> WindowsHelperOperationCreatedResponse:
    now = _now()
    operation = WindowsHelperOperation(
        operation_uuid=str(operation_id),
        access_node_id=access_node.id,
        source_endpoint_id=source_endpoint_id,
        source_profile_id=source_profile_id,
        operation_type=operation_type,
        request_json=_json(request),
        request_digest=canonical_protocol_digest(request),
        state="pending",
        expires_at=now + UNCLAIMED_OPERATION_TTL,
    )
    db.add(operation)
    db.commit()
    db.refresh(operation)
    return WindowsHelperOperationCreatedResponse(
        operation_id=operation_id,
        operation_type=operation_type,  # type: ignore[arg-type]
        state="pending",
        request_digest=operation.request_digest,
        expires_at=operation.expires_at,
        source_endpoint_id=source_endpoint_id,
        source_profile_id=source_profile_id,
    )


def create_probe_operation(
    db: Session,
    body: CreateWindowsHelperProbeOperationRequest,
) -> WindowsHelperOperationCreatedResponse:
    node = _load_access_node(db, body.access_node_id)
    source_endpoint_id = None
    if body.source_profile_id is not None:
        source, endpoint, _ = _profile_binding(db, body.source_profile_id, node)
        expected_source_type = endpoint.source_type
        if expected_source_type != body.source_type.value:
            raise WindowsHelperServiceError(
                "source_type_mismatch",
                "The requested Source type does not match the saved Endpoint.",
                http_status=409,
            )
        source_endpoint_id = endpoint.id
        if not source.source_root_path:
            raise WindowsHelperServiceError(
                "source_root_unavailable",
                "The Source Profile has no provider-native root.",
                http_status=409,
            )
        if ntpath.normcase(body.provider_native_root) != ntpath.normcase(source.source_root_path):
            raise WindowsHelperServiceError(
                "source_root_mismatch",
                "The requested root does not match the saved Source Profile.",
                http_status=409,
            )

    operation_id = uuid4()
    path = ProviderNativePath(
        provider_native_root=body.provider_native_root,
        provider_native_relative_path="",
        provider_native_full_path=body.provider_native_root,
    )
    request = HelperProbeRequest(
        request_id=operation_id,
        intended_access_node_id=body.access_node_id,
        source_type=body.source_type,
        probe_mode=body.probe_mode,
        provider_native_path=path,
        expected_collector_name=EXPECTED_COLLECTOR_NAME,
        expected_collector_version=EXPECTED_COLLECTOR_VERSION,
    )
    return _create_operation(
        db,
        operation_id=operation_id,
        access_node=node,
        operation_type="probe_source",
        request=request,
        source_endpoint_id=source_endpoint_id,
        source_profile_id=body.source_profile_id,
    )


def create_inventory_operation(
    db: Session,
    body: CreateWindowsHelperInventoryOperationRequest,
) -> WindowsHelperOperationCreatedResponse:
    probe_operation, probe = completed_probe(
        db,
        body.probe_operation_id,
        require_fresh=True,
        expected_source_profile_id=body.source_profile_id,
    )
    source, endpoint, node = _profile_binding(db, body.source_profile_id)
    if probe_operation.access_node_id != node.id:
        raise WindowsHelperServiceError(
            "access_node_mismatch",
            "The probe was completed by a different Access Node.",
            http_status=409,
        )
    from app.services.source_identity.identity_fingerprint import fingerprint_from_probe

    fingerprint = fingerprint_from_probe(probe)
    if (
        not endpoint.identity_fingerprint_hash
        or fingerprint.hash_value != endpoint.identity_fingerprint_hash
        or fingerprint.strength != "strong"
    ):
        raise WindowsHelperServiceError(
            "source_identity_mismatch",
            "Current Source identity does not match the enrolled Endpoint.",
            http_status=409,
        )

    if (body.inventory_generation is None) != (body.cursor is None):
        raise WindowsHelperServiceError(
            "invalid_cursor",
            "Inventory generation and cursor must be supplied together.",
            http_status=400,
        )
    if body.cursor is not None:
        _validate_inventory_continuation(
            db,
            source_profile_id=source.id,
            source_endpoint_id=endpoint.id,
            access_node_id=node.id,
            generation=body.inventory_generation,
            cursor=body.cursor,
            probe=probe,
        )

    operation_id = uuid4()
    request = HelperInventoryPageRequest(
        request_id=operation_id,
        intended_access_node_id=UUID(node.access_node_uuid),
        source_endpoint_id=endpoint.id,
        source_profile_id=source.id,
        source_type=probe.source_type,
        provider_native_path=ProviderNativePath(
            provider_native_root=probe.observed_path or "",
            provider_native_relative_path="",
            provider_native_full_path=probe.observed_path or "",
        ),
        expected_identity_fingerprint=endpoint.identity_fingerprint_hash,
        inventory_generation=body.inventory_generation,
        cursor=body.cursor,
        page_size=body.page_size,
    )
    return _create_operation(
        db,
        operation_id=operation_id,
        access_node=node,
        operation_type="inventory_page",
        request=request,
        source_endpoint_id=endpoint.id,
        source_profile_id=source.id,
    )


def _expire_stale(db: Session) -> None:
    now = _now()
    changed = False
    operations = list(
        db.scalars(
            select(WindowsHelperOperation).where(
                WindowsHelperOperation.state.in_(("pending", "claimed"))
            )
        )
    )
    for operation in operations:
        expired = (
            operation.state == "pending" and _aware(operation.expires_at) <= now
        ) or (
            operation.state == "claimed"
            and operation.lease_expires_at is not None
            and _aware(operation.lease_expires_at) <= now
        )
        if expired:
            operation.state = "expired"
            operation.error_code = "operation_expired"
            db.add(operation)
            changed = True
    if changed:
        db.commit()


def claim_operation(
    db: Session,
    credential: WindowsHelperCredential,
) -> HelperOperationClaimResponse:
    _expire_stale(db)
    now = _now()
    operation = db.scalar(
        select(WindowsHelperOperation)
        .where(
            WindowsHelperOperation.access_node_id == credential.access_node_id,
            WindowsHelperOperation.state == "pending",
            WindowsHelperOperation.expires_at > now,
        )
        .order_by(WindowsHelperOperation.created_at, WindowsHelperOperation.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if operation is None:
        return HelperOperationClaimResponse(operation=None, poll_after_seconds=HELPER_POLL_SECONDS)

    operation.state = "claimed"
    operation.claimed_at = now
    operation.lease_expires_at = now + CLAIM_LEASE
    operation.attempt_count += 1
    db.add(operation)
    db.commit()

    operation_id = UUID(operation.operation_uuid)
    if operation.operation_type not in {"probe_source", "inventory_page"}:
        operation.state = "failed"
        operation.error_code = "operation_unsupported"
        db.add(operation)
        db.commit()
        raise WindowsHelperServiceError(
            "operation_unsupported",
            "The queued Helper operation type is unsupported.",
            http_status=409,
        )

    try:
        if operation.operation_type == "probe_source":
            request = HelperProbeRequest.model_validate_json(operation.request_json)
            claimed = ClaimedProbeOperation(
                operation_id=operation_id,
                lease_expires_at=operation.lease_expires_at,
                request=request,
            )
        else:
            request = HelperInventoryPageRequest.model_validate_json(operation.request_json)
            claimed = ClaimedInventoryOperation(
                operation_id=operation_id,
                lease_expires_at=operation.lease_expires_at,
                request=request,
            )
    except ValueError as exc:
        operation.state = "failed"
        operation.error_code = "invalid_operation_request"
        db.add(operation)
        db.commit()
        raise WindowsHelperServiceError(
            "invalid_operation_request",
            "The queued Helper operation request is invalid.",
            http_status=409,
        ) from exc
    return HelperOperationClaimResponse(operation=claimed, poll_after_seconds=HELPER_POLL_SECONDS)


def _load_owned_operation(
    db: Session,
    credential: WindowsHelperCredential,
    operation_id: UUID,
) -> WindowsHelperOperation:
    operation = db.scalar(
        select(WindowsHelperOperation)
        .where(
            WindowsHelperOperation.operation_uuid == str(operation_id),
            WindowsHelperOperation.access_node_id == credential.access_node_id,
        )
        .with_for_update()
    )
    if operation is None:
        raise WindowsHelperServiceError(
            "operation_unavailable",
            "The Helper operation is unavailable.",
            http_status=404,
        )
    return operation


def _validate_completion_state(operation: WindowsHelperOperation, result_digest: str) -> bool:
    if operation.state == "completed":
        if operation.result_digest == result_digest:
            return True
        raise WindowsHelperServiceError(
            "operation_already_completed",
            "The Helper operation was already completed with a different result.",
            http_status=409,
        )
    if operation.state != "claimed":
        raise WindowsHelperServiceError(
            "operation_not_claimed",
            "The Helper operation is not claimable for completion.",
            http_status=409,
        )
    if operation.lease_expires_at is None or _aware(operation.lease_expires_at) <= _now():
        raise WindowsHelperServiceError(
            "operation_lease_expired",
            "The Helper operation lease expired.",
            http_status=409,
        )
    return False


def complete_probe_operation(
    db: Session,
    credential: WindowsHelperCredential,
    operation_id: UUID,
    result: HelperProbeResponse,
) -> HelperOperationCompletionResponse:
    operation = _load_owned_operation(db, credential, operation_id)
    if operation.operation_type != "probe_source":
        raise WindowsHelperServiceError("operation_type_mismatch", "Operation type mismatch.", http_status=409)
    request = HelperProbeRequest.model_validate_json(operation.request_json)
    if (
        result.request_id != operation_id
        or request.request_id != operation_id
        or request.intended_access_node_id is None
        or str(request.intended_access_node_id)
        != operation.access_node.access_node_uuid
        or result.source_type != request.source_type
        or result.provider_native_path != request.provider_native_path
        or result.collector_name != request.expected_collector_name
        or result.collector_version != request.expected_collector_version
    ):
        raise WindowsHelperServiceError(
            "operation_result_mismatch",
            "The Helper result does not match the authorized operation.",
            http_status=409,
        )
    return _complete(db, operation, result)


def complete_inventory_operation(
    db: Session,
    credential: WindowsHelperCredential,
    operation_id: UUID,
    result: HelperInventoryPageResponse,
) -> HelperOperationCompletionResponse:
    operation = _load_owned_operation(db, credential, operation_id)
    if operation.operation_type != "inventory_page":
        raise WindowsHelperServiceError("operation_type_mismatch", "Operation type mismatch.", http_status=409)
    request = HelperInventoryPageRequest.model_validate_json(operation.request_json)
    if (
        result.request_id != operation_id
        or request.request_id != operation_id
        or result.source_endpoint_id != request.source_endpoint_id
        or result.source_profile_id != request.source_profile_id
        or result.source_type != request.source_type
        or result.provider_native_path != request.provider_native_path
        or len(result.items) > request.page_size
        or (
            request.inventory_generation is not None
            and result.inventory_generation != request.inventory_generation
        )
    ):
        raise WindowsHelperServiceError(
            "operation_result_mismatch",
            "The Helper inventory result does not match the authorized operation.",
            http_status=409,
        )
    references = [item.candidate_reference for item in result.items]
    paths = [
        ntpath.normcase(item.provider_native_path.provider_native_relative_path)
        for item in result.items
    ]
    if len(references) != len(set(references)) or len(paths) != len(set(paths)):
        raise WindowsHelperServiceError(
            "inventory_result_ambiguous",
            "The Helper inventory result contains duplicate entries.",
            http_status=409,
        )
    if paths != sorted(paths):
        raise WindowsHelperServiceError(
            "inventory_result_not_ordered",
            "The Helper inventory result is not in deterministic Windows path order.",
            http_status=409,
        )
    for item in result.items:
        if (
            ntpath.normcase(item.provider_native_path.provider_native_root)
            != ntpath.normcase(request.provider_native_path.provider_native_root)
        ):
            raise WindowsHelperServiceError(
                "inventory_root_mismatch",
                "An inventory item is outside the authorized root.",
                http_status=409,
            )
    observed = adapt_probe_result(operation.access_node, result.identity_probe)
    from app.services.source_identity.identity_fingerprint import fingerprint_from_probe

    observed_fingerprint = fingerprint_from_probe(observed)
    identity_matches = (
        observed_fingerprint.strength == "strong"
        and observed_fingerprint.hash_value == request.expected_identity_fingerprint
    )
    if result.result_status == InventoryResultStatus.SUCCESS and not identity_matches:
        raise WindowsHelperServiceError(
            "source_identity_mismatch",
            "Inventory identity evidence does not match the enrolled Endpoint.",
            http_status=409,
        )
    serialized = _json(result)
    if len(serialized.encode("utf-8")) > MAX_INVENTORY_RESULT_BYTES:
        raise WindowsHelperServiceError(
            "inventory_result_too_large",
            "The inventory result exceeds the authorized size limit.",
            http_status=413,
        )
    return _complete(db, operation, result)


def _complete(
    db: Session,
    operation: WindowsHelperOperation,
    result: HelperProbeResponse | HelperInventoryPageResponse,
) -> HelperOperationCompletionResponse:
    result_digest = canonical_protocol_digest(result)
    replay = _validate_completion_state(operation, result_digest)
    if not replay:
        operation.state = "completed"
        operation.result_json = _json(result)
        operation.result_digest = result_digest
        operation.completed_at = _now()
        operation.error_code = None
        db.add(operation)
        db.commit()
    return HelperOperationCompletionResponse(
        operation_id=UUID(operation.operation_uuid),
        operation_type=operation.operation_type,  # type: ignore[arg-type]
        result_digest=result_digest,
        idempotent_replay=replay,
    )


def fail_operation(
    db: Session,
    credential: WindowsHelperCredential,
    operation_id: UUID,
    failure: HelperOperationFailureRequest,
) -> HelperOperationFailureResponse:
    operation = _load_owned_operation(db, credential, operation_id)
    if operation.state in _TERMINAL_STATES:
        raise WindowsHelperServiceError(
            "operation_terminal",
            "The Helper operation is already terminal.",
            http_status=409,
        )
    if operation.state != "claimed":
        raise WindowsHelperServiceError(
            "operation_not_claimed",
            "The Helper operation is not claimable for failure reporting.",
            http_status=409,
        )
    if operation.lease_expires_at is None or _aware(operation.lease_expires_at) <= _now():
        operation.state = "expired"
        operation.error_code = "operation_expired"
        db.add(operation)
        db.commit()
        raise WindowsHelperServiceError(
            "operation_lease_expired",
            "The Helper operation lease expired.",
            http_status=409,
        )
    operation.state = "failed"
    operation.error_code = failure.error_code
    operation.completed_at = _now()
    db.add(operation)
    db.commit()
    return HelperOperationFailureResponse(
        operation_id=operation_id,
        error_code=failure.error_code,
    )


def completed_probe(
    db: Session,
    operation_id: UUID,
    *,
    require_fresh: bool,
    expected_source_profile_id: int | None = None,
) -> tuple[WindowsHelperOperation, Any]:
    _expire_stale(db)
    operation = db.scalar(
        select(WindowsHelperOperation).where(
            WindowsHelperOperation.operation_uuid == str(operation_id)
        )
    )
    if (
        operation is None
        or operation.operation_type != "probe_source"
        or operation.state != "completed"
        or not operation.result_json
        or not operation.result_digest
        or operation.completed_at is None
    ):
        raise WindowsHelperServiceError(
            "probe_operation_not_completed",
            "The requested Source probe operation is not completed.",
            http_status=409,
        )
    if expected_source_profile_id is not None and operation.source_profile_id != expected_source_profile_id:
        raise WindowsHelperServiceError(
            "probe_profile_mismatch",
            "The Source probe operation is bound to a different Profile.",
            http_status=409,
        )
    if require_fresh and _aware(operation.completed_at) + COMPLETED_PROBE_FRESHNESS <= _now():
        raise WindowsHelperServiceError(
            "probe_operation_stale",
            "The completed Source probe is stale.",
            http_status=409,
        )
    result = HelperProbeResponse.model_validate_json(operation.result_json)
    if canonical_protocol_digest(result) != operation.result_digest:
        raise WindowsHelperServiceError(
            "probe_result_integrity_error",
            "The completed Source probe result failed integrity validation.",
            http_status=409,
        )
    return operation, adapt_probe_result(operation.access_node, result)


def _validate_inventory_continuation(
    db: Session,
    *,
    source_profile_id: int,
    source_endpoint_id: int,
    access_node_id: int,
    generation: UUID | None,
    cursor: str,
    probe: Any,
) -> None:
    candidates = list(
        db.scalars(
            select(WindowsHelperOperation).where(
                WindowsHelperOperation.operation_type == "inventory_page",
                WindowsHelperOperation.state == "completed",
                WindowsHelperOperation.source_profile_id == source_profile_id,
                WindowsHelperOperation.source_endpoint_id == source_endpoint_id,
                WindowsHelperOperation.access_node_id == access_node_id,
            )
        )
    )
    expected_root = ntpath.normcase(probe.observed_path or "")
    for operation in candidates:
        if not operation.result_json:
            continue
        result = HelperInventoryPageResponse.model_validate_json(operation.result_json)
        if (
            result.inventory_generation == generation
            and result.next_cursor == cursor
            and ntpath.normcase(result.provider_native_path.provider_native_root) == expected_root
        ):
            return
    raise WindowsHelperServiceError(
        "invalid_cursor",
        "The inventory continuation is invalid for this Source.",
        http_status=409,
    )


def get_operation_status(
    db: Session,
    operation_id: UUID,
) -> WindowsHelperOperationStatusResponse:
    _expire_stale(db)
    operation = db.scalar(
        select(WindowsHelperOperation).where(
            WindowsHelperOperation.operation_uuid == str(operation_id)
        )
    )
    if operation is None:
        raise WindowsHelperServiceError(
            "operation_not_found",
            "The Helper operation was not found.",
            http_status=404,
        )
    probe_result = None
    inventory_result = None
    candidates: list[WindowsInventoryCandidate] = []
    if operation.state == "completed" and operation.result_json:
        if operation.operation_type == "probe_source":
            probe_result = HelperProbeResponse.model_validate_json(operation.result_json)
        elif operation.operation_type == "inventory_page":
            inventory_result = HelperInventoryPageResponse.model_validate_json(operation.result_json)
            candidates = [_classify_inventory_item(item) for item in inventory_result.items]
    return WindowsHelperOperationStatusResponse(
        operation_id=UUID(operation.operation_uuid),
        operation_type=operation.operation_type,  # type: ignore[arg-type]
        state=operation.state,  # type: ignore[arg-type]
        request_digest=operation.request_digest,
        result_digest=operation.result_digest,
        created_at=operation.created_at,
        claimed_at=operation.claimed_at,
        completed_at=operation.completed_at,
        expires_at=operation.expires_at,
        lease_expires_at=operation.lease_expires_at,
        error_code=operation.error_code,
        source_endpoint_id=operation.source_endpoint_id,
        source_profile_id=operation.source_profile_id,
        probe_result=probe_result,
        inventory_result=inventory_result,
        inventory_candidates=candidates,
    )


def _classify_inventory_item(item: object) -> WindowsInventoryCandidate:
    entry_kind = item.entry_kind.value  # type: ignore[attr-defined]
    filename = item.filename  # type: ignore[attr-defined]
    size_bytes = item.size_bytes  # type: ignore[attr-defined]
    extension = PureWindowsPath(filename).suffix.casefold()
    if entry_kind != "regular_file":
        eligibility, reason = "rejected", entry_kind
    elif extension not in settings.approved_extensions:
        eligibility, reason = "rejected", "unsupported_extension"
    elif size_bytes is None or size_bytes < settings.minimum_file_size_bytes:
        eligibility, reason = "rejected", "below_minimum_size"
    else:
        eligibility, reason = "eligible", "current_linux_media_policy"
    path = item.provider_native_path  # type: ignore[attr-defined]
    return WindowsInventoryCandidate(
        candidate_reference=item.candidate_reference,  # type: ignore[attr-defined]
        provider_native_relative_path=path.provider_native_relative_path,
        provider_native_full_path=path.provider_native_full_path,
        filename=filename,
        size_bytes=size_bytes,
        modified_time_ns=item.modified_time_ns,  # type: ignore[attr-defined]
        entry_kind=entry_kind,
        eligibility=eligibility,
        eligibility_reason=reason,
    )


def helper_is_online(node: AccessNode) -> bool:
    return (
        node.status == "active"
        and node.last_seen_at is not None
        and _aware(node.last_seen_at) + HELPER_OFFLINE_AFTER > _now()
    )


def adapt_probe_result(
    node: AccessNode,
    result: HelperProbeResponse,
) -> Any:
    from app.services.source_identity.probe_schema import (
        AccessNodeSummary,
        IdentityFingerprintCandidate,
        SourceIdentityEvidenceItem,
        SourceIdentityProbeResponse,
        SourceIdentityProviderCapabilities,
        SourceRootCandidate,
    )

    evidence = [SourceIdentityEvidenceItem(**item.model_dump()) for item in result.evidence_items]

    def issue_items(items: list[object]) -> list[SourceIdentityEvidenceItem]:
        adapted: list[SourceIdentityEvidenceItem] = []
        by_code = {item.code: item for item in evidence}
        for issue in items:
            evidence_code = issue.evidence_code  # type: ignore[attr-defined]
            if evidence_code and evidence_code in by_code:
                adapted.append(by_code[evidence_code])
                continue
            code = evidence_code or issue.code.value  # type: ignore[attr-defined]
            adapted.append(
                SourceIdentityEvidenceItem(
                    category="path_evidence",
                    code=code,
                    status="blocked",
                    durability="volatile",
                    privacy_level="advanced_only",
                    source_types=[result.source_type.value],
                    message=issue.redacted_detail,  # type: ignore[attr-defined]
                    provider_name=result.collector_name,
                )
            )
        return adapted

    if result.result_status.value == "success":
        probe_status = "completed_with_warnings" if result.warnings else "completed"
        confidence = (
            "strong_match" if result.identity_fingerprint.available else "medium_needs_review"
        )
        safe_to_run = True
    elif result.result_status.value == "unavailable":
        probe_status, confidence, safe_to_run = "unavailable", "unavailable_not_connected", False
    elif result.result_status.value == "unsupported":
        probe_status, confidence, safe_to_run = "unsupported_provider", "unavailable_not_connected", False
    elif result.result_status.value in {"identity_mismatch", "identity_ambiguous"}:
        probe_status, confidence, safe_to_run = "blocked", "mismatch_block", False
    else:
        probe_status, confidence, safe_to_run = "blocked", "weak_manual_confirmation_required", False

    return SourceIdentityProbeResponse(
        probe_status=probe_status,
        source_type=result.source_type.value,
        os_family="windows",
        provider_name=result.collector_name,
        provider_version=result.collector_version,
        access_node_summary=AccessNodeSummary(
            access_node_id=node.access_node_uuid,
            label=node.label,
            os_family="windows",
            capabilities={
                "authenticated_helper": True,
                "remote_probe": True,
                "bounded_inventory": True,
            },
        ),
        observed_path=result.provider_native_path.provider_native_full_path,
        normalized_observed_path=ntpath.normcase(
            result.provider_native_path.provider_native_full_path
        ),
        source_root_candidate=SourceRootCandidate(**result.source_root_evidence.model_dump()),
        evidence_summary={},
        evidence_items=evidence,
        identity_fingerprint_candidate=IdentityFingerprintCandidate(
            **result.identity_fingerprint.model_dump()
        ),
        confidence_tier=confidence,
        match_status="not_compared",
        safe_to_run=safe_to_run,
        blockers=issue_items(list(result.blockers)),
        warnings=issue_items(list(result.warnings)),
        next_safe_actions=[
            item.next_action for item in result.blockers if item.next_action
        ],
        privacy_redaction_applied=True,
        capabilities=SourceIdentityProviderCapabilities(
            path_exists_check=True,
            path_readable_check=True,
            volume_identity=result.source_type.value != "nas",
            volume_guid=result.source_type.value in {
                "local",
                "external_device",
                "removable_media",
            },
            network_mapping=result.source_type.value == "nas",
            network_share_check=result.source_type.value == "nas",
            limitations=["Remote observation through the authenticated Windows Helper."],
        ),
    )

