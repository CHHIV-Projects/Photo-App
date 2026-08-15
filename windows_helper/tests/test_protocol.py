from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "app"))

from windows_helper_shared.identity.models import (  # noqa: E402
    IdentityFingerprintCandidate,
    NormalizedIdentityEvidence,
    ProviderNativeRootEvidence,
)
from windows_helper_shared.protocol import (  # noqa: E402
    CapabilityVersion,
    CollectorCapability,
    ErrorCode,
    HelperCapabilityIdentity,
    HelperProbeRequest,
    HelperProbeResponse,
    MachineIssue,
    ProbeResultStatus,
    ProtocolCompatibilityError,
    ProviderNativePath,
    canonical_protocol_digest,
    canonical_protocol_json,
    require_capability,
    require_protocol_version,
)


REQUEST_ID = UUID("11111111-2222-4333-8444-555555555555")


def _path() -> ProviderNativePath:
    return ProviderNativePath(
        provider_native_root="E:\\Photos",
        provider_native_relative_path="Family\\image.jpg",
        provider_native_full_path="E:\\Photos\\Family\\image.jpg",
    )


def _evidence(*, fingerprint_hash: str = "sha256:" + "a" * 64, message: str = "Display detail"):
    return NormalizedIdentityEvidence(
        category="volume_evidence",
        code="volume_guid_present",
        status="present",
        durability="durable",
        privacy_level="masked_only",
        source_types=["external_device"],
        masked_value="{...5555}",
        fingerprint_hash=fingerprint_hash,
        fingerprint_version="source_endpoint_volume_guid_v2",
        message=message,
    )


def _response(*, evidence=None, warning_detail: str | None = None) -> HelperProbeResponse:
    warnings = []
    if warning_detail is not None:
        warnings.append(MachineIssue(code=ErrorCode.UNAVAILABLE, redacted_detail=warning_detail))
    return HelperProbeResponse(
        request_id=REQUEST_ID,
        result_status=ProbeResultStatus.SUCCESS,
        source_type="external_device",
        provider_native_path=_path(),
        collector_name="windows_non_admin_probe",
        collector_version="1",
        source_root_evidence=ProviderNativeRootEvidence(
            path="E:\\Photos",
            is_valid_source_root_candidate=True,
            filesystem_boundary_type="external_folder",
            root_reason="Synthetic fixture.",
        ),
        evidence_items=[evidence or _evidence()],
        identity_fingerprint=IdentityFingerprintCandidate(algorithm="source_endpoint_volume_guid_v2", available=True),
        warnings=warnings,
    )


class ProtocolContractTests(unittest.TestCase):
    def test_v1_request_round_trip_is_strict_and_windows_native(self) -> None:
        request = HelperProbeRequest(
            request_id=REQUEST_ID,
            intended_access_node_id=UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"),
            source_type="external_device",
            provider_native_path=_path(),
            expected_collector_name="windows_non_admin_probe",
            expected_collector_version="1",
        )
        restored = HelperProbeRequest.model_validate_json(request.model_dump_json())
        self.assertEqual(restored, request)
        self.assertNotIn("/", restored.provider_native_path.provider_native_full_path)

    def test_unknown_fields_and_unsupported_versions_fail_closed(self) -> None:
        payload = {
            "request_id": str(REQUEST_ID),
            "source_type": "local",
            "provider_native_path": {
                "provider_native_root": "C:\\Photos",
                "provider_native_full_path": "C:\\Photos",
            },
            "expected_collector_name": "windows_non_admin_probe",
            "expected_collector_version": "1",
            "command": "whoami",
        }
        with self.assertRaises(ValidationError):
            HelperProbeRequest.model_validate(payload)
        payload.pop("command")
        payload["protocol_version"] = 2
        with self.assertRaises(ValidationError):
            HelperProbeRequest.model_validate(payload)
        with self.assertRaises(ProtocolCompatibilityError):
            require_protocol_version(2)

    def test_capability_identity_and_exact_compatibility(self) -> None:
        capabilities = HelperCapabilityIdentity(
            helper_version="0.1.0",
            supported_source_types=["local", "external_device"],
            collectors=[
                CollectorCapability(
                    name="windows_non_admin_probe",
                    version="1",
                    supported_source_types=["local", "external_device"],
                )
            ],
            capabilities=[CapabilityVersion(name="identity_probe", version="1")],
        )
        require_capability(capabilities.capabilities, "identity_probe", "1")
        with self.assertRaises(ProtocolCompatibilityError):
            require_capability(capabilities.capabilities, "identity_probe", "2")

    def test_duplicate_or_uncovered_capabilities_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            HelperCapabilityIdentity(
                helper_version="0.1.0",
                supported_source_types=["local", "local"],
                collectors=[
                    CollectorCapability(name="windows_probe", version="1", supported_source_types=["local"])
                ],
            )
        with self.assertRaises(ValidationError):
            HelperCapabilityIdentity(
                helper_version="0.1.0",
                supported_source_types=["optical_media"],
                collectors=[
                    CollectorCapability(name="windows_probe", version="1", supported_source_types=["local"])
                ],
            )

    def test_response_status_and_blocker_contract_is_fail_closed(self) -> None:
        with self.assertRaises(ValidationError):
            HelperProbeResponse(
                request_id=REQUEST_ID,
                result_status="invalid_root",
                source_type="local",
                provider_native_path=ProviderNativePath(
                    provider_native_root="C:\\Photos",
                    provider_native_full_path="C:\\Photos",
                ),
                collector_name="windows_probe",
                collector_version="1",
                source_root_evidence=ProviderNativeRootEvidence(),
            )

    def test_canonical_digest_is_stable_and_excludes_human_detail(self) -> None:
        first = _response(warning_detail="First display-only detail")
        second = _response(warning_detail="Different display-only detail")
        self.assertEqual(canonical_protocol_json(first), canonical_protocol_json(second))
        self.assertEqual(canonical_protocol_digest(first), canonical_protocol_digest(second))
        material_change = _response(evidence=_evidence(fingerprint_hash="sha256:" + "b" * 64))
        self.assertNotEqual(canonical_protocol_digest(first), canonical_protocol_digest(material_change))

    def test_canonical_digest_normalizes_windows_case_and_capability_order(self) -> None:
        first_request = HelperProbeRequest(
            request_id=REQUEST_ID,
            source_type="external_device",
            provider_native_path=_path(),
            expected_collector_name="windows_non_admin_probe",
            expected_collector_version="1",
        )
        second_request = first_request.model_copy(
            update={
                "provider_native_path": ProviderNativePath(
                    provider_native_root="e:\\photos",
                    provider_native_relative_path="family\\IMAGE.JPG",
                    provider_native_full_path="e:\\photos\\family\\IMAGE.JPG",
                )
            }
        )
        self.assertEqual(canonical_protocol_digest(first_request), canonical_protocol_digest(second_request))

        first_capabilities = HelperCapabilityIdentity(
            helper_version="0.1.0",
            supported_source_types=["local", "external_device"],
            collectors=[
                CollectorCapability(
                    name="windows_probe",
                    version="1",
                    supported_source_types=["local", "external_device"],
                )
            ],
            capabilities=[
                CapabilityVersion(name="identity_probe", version="1"),
                CapabilityVersion(name="path_contract", version="1"),
            ],
        )
        reordered = HelperCapabilityIdentity(
            helper_version="0.1.0",
            supported_source_types=["external_device", "local"],
            collectors=[
                CollectorCapability(
                    name="windows_probe",
                    version="1",
                    supported_source_types=["external_device", "local"],
                )
            ],
            capabilities=list(reversed(first_capabilities.capabilities)),
        )
        self.assertEqual(canonical_protocol_digest(first_capabilities), canonical_protocol_digest(reordered))

    def test_error_schema_cannot_carry_raw_command_output_or_secrets(self) -> None:
        issue = MachineIssue(code="probe_failed", redacted_detail="The read-only probe failed.")
        payload = issue.model_dump()
        self.assertNotIn("command", payload)
        self.assertNotIn("stdout", payload)
        self.assertNotIn("stderr", payload)
        self.assertNotIn("token", payload)
        with self.assertRaises(ValidationError):
            MachineIssue.model_validate(
                {"code": "probe_failed", "raw_powershell_output": "secret transcript"}
            )

    def test_protocol_has_no_linux_vault_command_or_upload_authority(self) -> None:
        field_names = set()
        for model in (HelperCapabilityIdentity, HelperProbeRequest, HelperProbeResponse, MachineIssue):
            field_names.update(model.model_fields)
        forbidden = {"linux_path", "receiving_path", "vault_path", "database_path", "command", "upload"}
        self.assertTrue(forbidden.isdisjoint(field_names))
        serialized = json.dumps(sorted(field_names))
        self.assertNotIn("password", serialized)
        self.assertNotIn("token", serialized)

    def test_bounded_fields_reject_oversized_values(self) -> None:
        with self.assertRaises(ValidationError):
            CapabilityVersion(name="x" * 65, version="1")
        with self.assertRaises(ValidationError):
            MachineIssue(code="probe_failed", redacted_detail="x" * 513)


if __name__ == "__main__":
    unittest.main()
