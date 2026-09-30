"""Process-local, child-bound physical identity attestations."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import ntpath
import secrets
from typing import Literal

from windows_helper_shared.channel import ClaimedChildAttestationOperation
from windows_helper_shared.protocol import (
    HelperAcquireItemRequest,
    HelperChildAttestationResponse,
    HelperProbeRequest,
)

from .operations import execute_probe
from windows_helper_shared.identity.windows import WindowsIdentityCollector


AttestationValidation = Literal["valid", "refresh_required", "binding_mismatch"]


class ChildIdentityMismatch(RuntimeError):
    """The full child probe did not prove the approved physical Source."""


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class ChildAttestationAuthority:
    """Signs bounded tokens with a key that intentionally dies with this process."""

    def __init__(self, signing_key: bytes | None = None) -> None:
        self._key = signing_key or secrets.token_bytes(32)

    def attest(
        self,
        operation: ClaimedChildAttestationOperation,
        collector: WindowsIdentityCollector,
        *,
        now: datetime | None = None,
    ) -> HelperChildAttestationResponse:
        request = operation.request
        probe = execute_probe(
            collector,
            HelperProbeRequest(
                request_id=operation.operation_id,
                intended_access_node_id=request.intended_access_node_id,
                source_type=request.source_type,
                probe_mode="run_launch_verification",
                provider_native_path=request.provider_native_path,
                expected_collector_name="windows_non_admin_probe_v1",
                expected_collector_version="1",
            ),
        )
        hashes = {
            item.fingerprint_hash
            for item in probe.evidence_items
            if item.fingerprint_hash and item.fingerprint_version
        }
        if probe.result_status.value != "success" or hashes != {request.expected_identity_fingerprint}:
            raise ChildIdentityMismatch(
                "Child physical identity did not match the authorized Source."
            )
        issued_at = now or datetime.now(timezone.utc)
        expires_at = issued_at + timedelta(seconds=request.attestation_lifetime_seconds)
        payload = self._payload(
            access_node_id=str(request.intended_access_node_id),
            source_endpoint_id=request.source_endpoint_id,
            source_profile_id=request.source_profile_id,
            source_type=request.source_type.value,
            fingerprint=request.expected_identity_fingerprint,
            root=request.provider_native_path.provider_native_root,
            parent_workflow_id=str(request.parent_workflow_id),
            acquisition_run_id=str(request.acquisition_run_id),
            issued_at=issued_at,
            expires_at=expires_at,
        )
        encoded = _b64encode(payload)
        signature = _b64encode(hmac.new(self._key, payload, hashlib.sha256).digest())
        return HelperChildAttestationResponse(
            request_id=operation.operation_id,
            intended_access_node_id=request.intended_access_node_id,
            source_endpoint_id=request.source_endpoint_id,
            source_profile_id=request.source_profile_id,
            source_type=request.source_type,
            provider_native_path=request.provider_native_path,
            expected_identity_fingerprint=request.expected_identity_fingerprint,
            parent_workflow_id=request.parent_workflow_id,
            acquisition_run_id=request.acquisition_run_id,
            issued_at=issued_at,
            expires_at=expires_at,
            attestation_token=f"cat1.{encoded}.{signature}",
        )

    def validate(
        self,
        request: HelperAcquireItemRequest,
        *,
        now: datetime | None = None,
    ) -> AttestationValidation:
        token = request.child_attestation_token
        if not token or request.parent_workflow_id is None:
            return "refresh_required"
        try:
            prefix, encoded, supplied_signature = token.split(".", 2)
            if prefix != "cat1":
                return "refresh_required"
            payload = _b64decode(encoded)
            expected_signature = _b64encode(hmac.new(self._key, payload, hashlib.sha256).digest())
            if not hmac.compare_digest(supplied_signature, expected_signature):
                return "refresh_required"
            values = json.loads(payload.decode("utf-8"))
        except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
            return "refresh_required"
        expected = {
            "version": "child-attestation-v1",
            "access_node_id": str(request.intended_access_node_id),
            "source_endpoint_id": request.source_endpoint_id,
            "source_profile_id": request.source_profile_id,
            "source_type": request.source_type.value,
            "fingerprint": request.expected_identity_fingerprint,
            "root": ntpath.normcase(ntpath.normpath(request.provider_native_path.provider_native_root)),
            "parent_workflow_id": str(request.parent_workflow_id),
            "acquisition_run_id": str(request.acquisition_run_id),
        }
        if any(values.get(key) != value for key, value in expected.items()):
            return "binding_mismatch"
        try:
            expires_at = datetime.fromisoformat(values["expires_at"])
        except (KeyError, TypeError, ValueError):
            return "refresh_required"
        current = now or datetime.now(timezone.utc)
        return "valid" if expires_at > current else "refresh_required"

    @staticmethod
    def _payload(**values: object) -> bytes:
        values["version"] = "child-attestation-v1"
        values["root"] = ntpath.normcase(ntpath.normpath(str(values["root"])))
        values["issued_at"] = values["issued_at"].isoformat()  # type: ignore[union-attr]
        values["expires_at"] = values["expires_at"].isoformat()  # type: ignore[union-attr]
        return json.dumps(values, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
