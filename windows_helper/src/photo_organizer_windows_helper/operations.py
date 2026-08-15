"""Read-only execution of the two recognized Helper operation types."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import ntpath
import os
import stat
from collections.abc import Iterator
from uuid import UUID, uuid4

from windows_helper_shared.channel import (
    ClaimedInventoryOperation,
    ClaimedProbeOperation,
)
from windows_helper_shared.identity.models import IdentityCollectionRequest
from windows_helper_shared.identity.windows import WindowsIdentityCollector
from windows_helper_shared.protocol import (
    HelperInventoryItem,
    HelperInventoryPageRequest,
    HelperInventoryPageResponse,
    HelperProbeRequest,
    HelperProbeResponse,
    InventoryEntryKind,
    InventoryResultStatus,
    MAX_INVENTORY_RESULT_BYTES,
    ProviderNativePath,
    probe_response_from_collection,
)


_REPARSE_ATTRIBUTE = 0x400


@dataclass
class _GenerationState:
    root: str
    expected_identity_fingerprint: str
    iterator: Iterator[HelperInventoryItem]
    cursor: str
    pending: HelperInventoryItem | None = None


class WindowsInventoryCollector:
    """Process-local bounded paging state; Helper restart invalidates cursors."""

    def __init__(self, identity_collector: WindowsIdentityCollector | None = None) -> None:
        self._identity_collector = identity_collector or WindowsIdentityCollector()
        self._generations: dict[UUID, _GenerationState] = {}

    def inventory_page(
        self,
        request: HelperInventoryPageRequest,
    ) -> HelperInventoryPageResponse:
        probe_request = HelperProbeRequest(
            request_id=request.request_id,
            intended_access_node_id=request.intended_access_node_id,
            source_type=request.source_type,
            probe_mode="readiness_probe",
            provider_native_path=request.provider_native_path,
            expected_collector_name="windows_non_admin_probe_v1",
            expected_collector_version="1",
        )
        identity_probe = execute_probe(self._identity_collector, probe_request)
        observed_fingerprint = _strong_fingerprint_hash(identity_probe)
        if identity_probe.result_status.value != "success":
            return HelperInventoryPageResponse(
                request_id=request.request_id,
                result_status=InventoryResultStatus.SOURCE_UNAVAILABLE,
                source_endpoint_id=request.source_endpoint_id,
                source_profile_id=request.source_profile_id,
                source_type=request.source_type,
                provider_native_path=request.provider_native_path,
                inventory_generation=request.inventory_generation or uuid4(),
                identity_probe=identity_probe,
            )
        if observed_fingerprint != request.expected_identity_fingerprint:
            return HelperInventoryPageResponse(
                request_id=request.request_id,
                result_status=InventoryResultStatus.IDENTITY_CHANGED,
                source_endpoint_id=request.source_endpoint_id,
                source_profile_id=request.source_profile_id,
                source_type=request.source_type,
                provider_native_path=request.provider_native_path,
                inventory_generation=request.inventory_generation or uuid4(),
                identity_probe=identity_probe,
            )

        if request.inventory_generation is None:
            generation = uuid4()
            cursor = _new_cursor()
            state = _GenerationState(
                root=request.provider_native_path.provider_native_root,
                expected_identity_fingerprint=request.expected_identity_fingerprint,
                iterator=self._walk(
                    request.provider_native_path.provider_native_root,
                    generation,
                ),
                cursor=cursor,
            )
            self._generations[generation] = state
        else:
            generation = request.inventory_generation
            state = self._generations.get(generation)
            if (
                state is None
                or request.cursor != state.cursor
                or ntpath.normcase(state.root)
                != ntpath.normcase(request.provider_native_path.provider_native_root)
                or state.expected_identity_fingerprint
                != request.expected_identity_fingerprint
            ):
                return HelperInventoryPageResponse(
                    request_id=request.request_id,
                    result_status=InventoryResultStatus.INVALID_CURSOR,
                    source_endpoint_id=request.source_endpoint_id,
                    source_profile_id=request.source_profile_id,
                    source_type=request.source_type,
                    provider_native_path=request.provider_native_path,
                    inventory_generation=generation,
                    identity_probe=identity_probe,
                )

        items: list[HelperInventoryItem] = []
        while len(items) < request.page_size:
            item = state.pending
            state.pending = None
            if item is None:
                try:
                    item = next(state.iterator)
                except StopIteration:
                    break
            tentative = _response(
                request=request,
                generation=generation,
                identity_probe=identity_probe,
                items=[*items, item],
                next_cursor="x" * 32,
            )
            if len(_serialized(tentative)) > MAX_INVENTORY_RESULT_BYTES:
                state.pending = item
                if not items:
                    raise RuntimeError("One inventory item exceeds the bounded result size.")
                break
            items.append(item)

        has_more = state.pending is not None
        if not has_more:
            try:
                state.pending = next(state.iterator)
                has_more = True
            except StopIteration:
                has_more = False

        if has_more:
            state.cursor = _new_cursor()
            next_cursor = state.cursor
        else:
            next_cursor = None
            self._generations.pop(generation, None)

        result = _response(
            request=request,
            generation=generation,
            identity_probe=identity_probe,
            items=items,
            next_cursor=next_cursor,
        )
        if len(_serialized(result)) > MAX_INVENTORY_RESULT_BYTES:
            raise RuntimeError("Inventory response exceeds the bounded result size.")
        return result

    def _walk(self, root: str, generation: UUID) -> Iterator[HelperInventoryItem]:
        def walk_directory(directory: str) -> Iterator[HelperInventoryItem]:
            try:
                entries = sorted(
                    os.scandir(directory),
                    key=lambda item: ntpath.normcase(item.name),
                )
            except OSError:
                if ntpath.normcase(directory) == ntpath.normcase(root):
                    raise
                yield _item(
                    root=root,
                    full_path=directory,
                    generation=generation,
                    entry_kind=InventoryEntryKind.INACCESSIBLE,
                )
                return

            for entry in entries:
                full_path = entry.path
                try:
                    metadata = entry.stat(follow_symlinks=False)
                    is_reparse = entry.is_symlink() or bool(
                        getattr(metadata, "st_file_attributes", 0) & _REPARSE_ATTRIBUTE
                    )
                    if is_reparse:
                        yield _item(
                            root=root,
                            full_path=full_path,
                            generation=generation,
                            entry_kind=InventoryEntryKind.REPARSE_POINT,
                            metadata=metadata,
                        )
                    elif stat.S_ISDIR(metadata.st_mode):
                        yield from walk_directory(full_path)
                    elif stat.S_ISREG(metadata.st_mode):
                        yield _item(
                            root=root,
                            full_path=full_path,
                            generation=generation,
                            entry_kind=InventoryEntryKind.REGULAR_FILE,
                            metadata=metadata,
                        )
                    else:
                        yield _item(
                            root=root,
                            full_path=full_path,
                            generation=generation,
                            entry_kind=InventoryEntryKind.SPECIAL,
                            metadata=metadata,
                        )
                except OSError:
                    yield _item(
                        root=root,
                        full_path=full_path,
                        generation=generation,
                        entry_kind=InventoryEntryKind.INACCESSIBLE,
                    )

        yield from walk_directory(root)


class HelperOperationExecutor:
    def __init__(
        self,
        identity_collector: WindowsIdentityCollector | None = None,
        inventory_collector: WindowsInventoryCollector | None = None,
    ) -> None:
        self._identity_collector = identity_collector or WindowsIdentityCollector()
        self._inventory_collector = inventory_collector or WindowsInventoryCollector(
            self._identity_collector
        )

    def execute(
        self,
        operation: ClaimedProbeOperation | ClaimedInventoryOperation,
    ) -> HelperProbeResponse | HelperInventoryPageResponse:
        if isinstance(operation, ClaimedProbeOperation):
            return execute_probe(self._identity_collector, operation.request)
        if isinstance(operation, ClaimedInventoryOperation):
            return self._inventory_collector.inventory_page(operation.request)
        raise ValueError("Unsupported Helper operation type.")


def execute_probe(
    collector: WindowsIdentityCollector,
    request: HelperProbeRequest,
) -> HelperProbeResponse:
    result = collector.collect(
        IdentityCollectionRequest(
            source_type=request.source_type.value,
            observed_path=request.provider_native_path.provider_native_full_path,
            probe_mode=request.probe_mode.value,
            access_node_id=(
                str(request.intended_access_node_id)
                if request.intended_access_node_id is not None
                else None
            ),
            comparison_requested=False,
        )
    )
    return probe_response_from_collection(request=request, result=result)


def _item(
    *,
    root: str,
    full_path: str,
    generation: UUID,
    entry_kind: InventoryEntryKind,
    metadata: os.stat_result | None = None,
) -> HelperInventoryItem:
    relative = ntpath.relpath(full_path, root)
    if relative in {"", "."} or relative == ".." or relative.startswith("..\\"):
        raise RuntimeError("Inventory entry escaped the authorized root.")
    candidate_reference = hashlib.sha256(
        (
            "photo-organizer-windows-inventory-candidate-v1\x00"
            + str(generation)
            + "\x00"
            + ntpath.normcase(relative)
        ).encode("utf-8")
    ).hexdigest()
    stable_id = None
    if metadata is not None and getattr(metadata, "st_ino", 0):
        stable_id = "sha256:" + hashlib.sha256(
            (
                "photo-organizer-windows-file-id-v1\x00"
                + str(getattr(metadata, "st_dev", 0))
                + ":"
                + str(metadata.st_ino)
            ).encode("utf-8")
        ).hexdigest()
    return HelperInventoryItem(
        candidate_reference=candidate_reference,
        provider_native_path=ProviderNativePath(
            provider_native_root=root,
            provider_native_relative_path=relative,
            provider_native_full_path=full_path,
        ),
        filename=ntpath.basename(full_path),
        size_bytes=metadata.st_size if metadata is not None else None,
        modified_time_ns=metadata.st_mtime_ns if metadata is not None else None,
        entry_kind=entry_kind,
        stable_file_id_digest=stable_id,
    )


def _response(
    *,
    request: HelperInventoryPageRequest,
    generation: UUID,
    identity_probe: HelperProbeResponse,
    items: list[HelperInventoryItem],
    next_cursor: str | None,
) -> HelperInventoryPageResponse:
    return HelperInventoryPageResponse(
        request_id=request.request_id,
        result_status=InventoryResultStatus.SUCCESS,
        source_endpoint_id=request.source_endpoint_id,
        source_profile_id=request.source_profile_id,
        source_type=request.source_type,
        provider_native_path=request.provider_native_path,
        inventory_generation=generation,
        identity_probe=identity_probe,
        items=items,
        next_cursor=next_cursor,
    )


def _serialized(result: HelperInventoryPageResponse) -> bytes:
    return json.dumps(
        result.model_dump(mode="json", exclude_none=True),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _strong_fingerprint_hash(result: HelperProbeResponse) -> str | None:
    hashes = {
        item.fingerprint_hash
        for item in result.evidence_items
        if item.fingerprint_hash and item.fingerprint_version
    }
    return next(iter(hashes)) if len(hashes) == 1 else None


def _new_cursor() -> str:
    return uuid4().hex

