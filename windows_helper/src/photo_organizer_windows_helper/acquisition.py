"""Exact read-only Windows acquisition execution for one authorized item."""

from __future__ import annotations

import hashlib
import ntpath
import os
import stat
from typing import BinaryIO, Callable

from windows_helper_shared.channel import ClaimedAcquireOperation
from windows_helper_shared.identity.models import IdentityCollectionRequest
from windows_helper_shared.identity.windows import WindowsIdentityCollector
from windows_helper_shared.protocol import (
    AcquireResultStatus,
    HelperAcquireItemResponse,
    HelperProbeRequest,
    SourceFileEvidence,
)

from .client import HelperApiClient, HelperClientError
from .credential_store import StoredCredential
from .operations import execute_probe, local_residency


_REPARSE_ATTRIBUTE = 0x400


def _stable_file_id(metadata: os.stat_result) -> str | None:
    if not getattr(metadata, "st_ino", 0):
        return None
    return "sha256:" + hashlib.sha256(
        (
            "photo-organizer-windows-file-id-v1\x00"
            + str(getattr(metadata, "st_dev", 0))
            + ":"
            + str(metadata.st_ino)
        ).encode("utf-8")
    ).hexdigest()


def _evidence(metadata: os.stat_result) -> SourceFileEvidence:
    attributes = getattr(metadata, "st_file_attributes", None)
    return SourceFileEvidence(
        size_bytes=metadata.st_size,
        modified_time_ns=metadata.st_mtime_ns,
        stable_file_id_digest=_stable_file_id(metadata),
        windows_file_attributes=attributes,
        local_residency=local_residency(metadata),
    )


def _matches_expected(request: object, evidence: SourceFileEvidence) -> bool:
    return (
        evidence.size_bytes == request.expected_size_bytes
        and evidence.modified_time_ns == request.expected_modified_time_ns
        and (
            request.expected_file_id_digest is None
            or evidence.stable_file_id_digest == request.expected_file_id_digest
        )
        and (
            request.expected_windows_file_attributes is None
            or evidence.windows_file_attributes == request.expected_windows_file_attributes
        )
        and evidence.local_residency == request.expected_local_residency == "resident"
        and not ((evidence.windows_file_attributes or 0) & _REPARSE_ATTRIBUTE)
    )


def _open_exact_readonly(path: str) -> BinaryIO:
    if os.name != "nt":
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        return os.fdopen(fd, "rb", buffering=0)
    import ctypes
    import msvcrt
    from ctypes import wintypes

    create_file = ctypes.windll.kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    handle = create_file(
        path,
        0x80000000,
        0x00000001,
        None,
        3,
        0x00200000 | 0x08000000,
        None,
    )
    invalid = ctypes.c_void_p(-1).value
    if handle == invalid:
        raise OSError("Windows Source file could not be opened safely.")
    try:
        fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | getattr(os, "O_BINARY", 0))
    except BaseException:
        ctypes.windll.kernel32.CloseHandle(handle)
        raise
    return os.fdopen(fd, "rb", buffering=0)


def _opened_handle_path(source: BinaryIO) -> str | None:
    if os.name != "nt":
        return None
    import ctypes
    import msvcrt

    get_path = ctypes.windll.kernel32.GetFinalPathNameByHandleW
    from ctypes import wintypes

    get_path.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    get_path.restype = wintypes.DWORD
    handle = msvcrt.get_osfhandle(source.fileno())
    required = get_path(handle, None, 0, 0)
    if required <= 0 or required > 32768:
        raise OSError("Windows Source handle path could not be verified.")
    buffer = ctypes.create_unicode_buffer(required + 1)
    written = get_path(handle, buffer, len(buffer), 0)
    if written <= 0 or written >= len(buffer):
        raise OSError("Windows Source handle path could not be verified.")
    path = buffer.value
    if path.startswith("\\\\?\\UNC\\"):
        path = "\\\\" + path[8:]
    elif path.startswith("\\\\?\\"):
        path = path[4:]
    return ntpath.normcase(ntpath.normpath(path))


def _failed(operation: ClaimedAcquireOperation, status: AcquireResultStatus, code: str) -> HelperAcquireItemResponse:
    request = operation.request
    return HelperAcquireItemResponse(
        request_id=operation.operation_id, result_status=status,
        acquisition_run_id=request.acquisition_run_id,
        acquisition_item_id=request.acquisition_item_id,
        source_endpoint_id=request.source_endpoint_id,
        source_profile_id=request.source_profile_id,
        source_type=request.source_type,
        provider_native_path=request.provider_native_path,
        error_code=code,
    )


def execute_acquisition(
    operation: ClaimedAcquireOperation,
    client: HelperApiClient,
    credential: StoredCredential,
    *,
    identity_collector: WindowsIdentityCollector | None = None,
    open_file: Callable[[str], BinaryIO] = _open_exact_readonly,
    handle_path: Callable[[BinaryIO], str | None] = _opened_handle_path,
    stat_path: Callable[[str], os.stat_result] = lambda path: os.stat(path, follow_symlinks=False),
) -> HelperAcquireItemResponse:
    request = operation.request
    collector = identity_collector or WindowsIdentityCollector()
    probe = execute_probe(
        collector,
        HelperProbeRequest(
            request_id=operation.operation_id,
            intended_access_node_id=request.intended_access_node_id,
            source_type=request.source_type,
            probe_mode="run_launch_verification",
            provider_native_path=request.provider_native_path.model_copy(
                update={
                    "provider_native_relative_path": "",
                    "provider_native_full_path": request.provider_native_path.provider_native_root,
                }
            ),
            expected_collector_name="windows_non_admin_probe_v1",
            expected_collector_version="1",
        ),
    )
    observed_hashes = {
        evidence.fingerprint_hash
        for evidence in probe.evidence_items
        if evidence.fingerprint_hash and evidence.fingerprint_version
    }
    if probe.result_status.value != "success" or observed_hashes != {request.expected_identity_fingerprint}:
        return _failed(operation, AcquireResultStatus.SOURCE_CHANGED, "source_identity_changed")
    path = request.provider_native_path.provider_native_full_path
    try:
        pre_path_metadata = stat_path(path)
    except OSError:
        return _failed(operation, AcquireResultStatus.SOURCE_UNAVAILABLE, "source_unavailable")
    pre_path_evidence = _evidence(pre_path_metadata)
    if pre_path_evidence.local_residency != "resident":
        return _failed(operation, AcquireResultStatus.PLACEHOLDER_UNAVAILABLE, "cloud_placeholder_unavailable")
    if not stat.S_ISREG(pre_path_metadata.st_mode) or not _matches_expected(request, pre_path_evidence):
        return _failed(operation, AcquireResultStatus.SOURCE_CHANGED, "source_evidence_changed")
    status_response = client.acquisition_status(
        credential, operation.operation_id, request.acquisition_run_id, request.acquisition_item_id
    )
    if (
        status_response.state not in {"transferring", "verifying"}
        or status_response.expected_size_bytes != request.expected_size_bytes
        or status_response.maximum_chunk_bytes < request.normal_chunk_bytes
        or status_response.committed_offset > request.expected_size_bytes
    ):
        return _failed(operation, AcquireResultStatus.TRANSFER_FAILED, "receiving_state_invalid")
    digest = hashlib.sha256()
    total_read = 0
    try:
        source_context = open_file(path)
    except OSError:
        return _failed(operation, AcquireResultStatus.SOURCE_UNAVAILABLE, "source_unavailable")
    with source_context as source:
        try:
            observed_handle_path = handle_path(source)
        except OSError:
            return _failed(operation, AcquireResultStatus.SOURCE_CHANGED, "source_handle_unverified")
        if observed_handle_path is not None and observed_handle_path != ntpath.normcase(ntpath.normpath(path)):
            return _failed(operation, AcquireResultStatus.SOURCE_CHANGED, "source_path_changed")

        try:
            pre_evidence = _evidence(os.fstat(source.fileno()))
        except OSError:
            return _failed(operation, AcquireResultStatus.SOURCE_UNAVAILABLE, "source_unavailable")
        if not _matches_expected(request, pre_evidence):
            return _failed(operation, AcquireResultStatus.SOURCE_CHANGED, "source_evidence_changed")
        while total_read < status_response.committed_offset:
            try:
                block = source.read(min(request.normal_chunk_bytes, status_response.committed_offset - total_read))
            except OSError:
                return _failed(operation, AcquireResultStatus.SOURCE_UNAVAILABLE, "source_unavailable")
            if not block:
                return _failed(operation, AcquireResultStatus.SOURCE_CHANGED, "source_short_read")
            digest.update(block)
            total_read += len(block)
        offset = status_response.committed_offset
        while offset < request.expected_size_bytes:
            try:
                chunk = source.read(min(request.normal_chunk_bytes, request.expected_size_bytes - offset))
            except OSError:
                return _failed(operation, AcquireResultStatus.SOURCE_UNAVAILABLE, "source_unavailable")
            if not chunk:
                return _failed(operation, AcquireResultStatus.SOURCE_CHANGED, "source_short_read")
            digest.update(chunk)
            chunk_digest = "sha256:" + hashlib.sha256(chunk).hexdigest()
            try:
                committed = client.upload_chunk(
                    credential, operation.operation_id, request.acquisition_run_id,
                    request.acquisition_item_id, offset=offset, chunk=chunk, digest=chunk_digest,
                )
            except HelperClientError:
                recovered = client.acquisition_status(
                    credential, operation.operation_id, request.acquisition_run_id, request.acquisition_item_id
                )
                if recovered.committed_offset == offset:
                    committed = client.upload_chunk(
                        credential, operation.operation_id, request.acquisition_run_id,
                        request.acquisition_item_id, offset=offset, chunk=chunk, digest=chunk_digest,
                    )
                elif recovered.committed_offset == offset + len(chunk):
                    committed = recovered
                else:
                    raise
            if committed.committed_offset != offset + len(chunk):
                raise HelperClientError("Linux committed offset did not advance exactly.")
            offset += len(chunk)
            total_read += len(chunk)
        try:
            trailing = source.read(1)
        except OSError:
            return _failed(operation, AcquireResultStatus.SOURCE_UNAVAILABLE, "source_unavailable")
        if trailing:
            return _failed(operation, AcquireResultStatus.SOURCE_CHANGED, "source_size_changed")
        try:
            post_evidence = _evidence(os.fstat(source.fileno()))
        except OSError:
            return _failed(operation, AcquireResultStatus.SOURCE_CHANGED, "source_evidence_changed")
    try:
        post_path_evidence = _evidence(stat_path(path))
    except OSError:
        return _failed(operation, AcquireResultStatus.SOURCE_CHANGED, "source_evidence_changed")
    if pre_evidence != post_evidence or post_evidence != post_path_evidence or not _matches_expected(request, post_evidence):
        return _failed(operation, AcquireResultStatus.SOURCE_CHANGED, "source_evidence_changed")
    return HelperAcquireItemResponse(
        request_id=operation.operation_id,
        result_status=AcquireResultStatus.SUCCESS,
        acquisition_run_id=request.acquisition_run_id,
        acquisition_item_id=request.acquisition_item_id,
        source_endpoint_id=request.source_endpoint_id,
        source_profile_id=request.source_profile_id,
        source_type=request.source_type,
        provider_native_path=request.provider_native_path,
        pre_read_evidence=pre_evidence,
        post_read_evidence=post_evidence,
        bytes_read=total_read,
        helper_source_sha256="sha256:" + digest.hexdigest(),
    )
