from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any
from uuid import UUID


SHARED_ROOT = Path(__file__).resolve().parents[2] / "backend" / "app"
sys.path.insert(0, str(SHARED_ROOT))

from windows_helper_shared.identity.fingerprints import (  # noqa: E402
    nas_server_share_fingerprint,
    optical_media_fingerprint_v2,
    volume_guid_fingerprint,
)
from windows_helper_shared.identity.models import (  # noqa: E402
    CommandResult,
    IdentityCollectionRequest,
)
from windows_helper_shared.identity.windows import (  # noqa: E402
    PathProbeStatus,
    WindowsIdentityCollector,
)
from windows_helper_shared.paths import ProviderNativePathError, normalize_provider_native_root  # noqa: E402
from windows_helper_shared.protocol import (  # noqa: E402
    HelperProbeRequest,
    ProviderNativePath,
    probe_response_from_collection,
)


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "windows_identity_golden_v1.json"


class _FakeRunner:
    def run(self, args: list[str], *, timeout_seconds: float) -> CommandResult:
        return CommandResult(args=tuple(args), returncode=0, stdout="")


def _fingerprint(case: dict[str, Any]) -> tuple[str, str]:
    kind = case["identity_kind"]
    value = case.get("identity_input")
    if kind == "volume_guid":
        return volume_guid_fingerprint(value)
    if kind == "nas_server_share":
        return nas_server_share_fingerprint(value["server"], value["share"])
    if kind == "optical_v2":
        return optical_media_fingerprint_v2(value)
    raise AssertionError(f"Unsupported fixture identity kind: {kind}")


class GoldenIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.cases = {case["name"]: case for case in cls.fixture["cases"]}

    def test_golden_fingerprints_match_exactly(self) -> None:
        self.assertEqual(self.fixture["fixture_version"], 1)
        for case in self.fixture["cases"]:
            if case["identity_kind"] == "invalid_path":
                continue
            with self.subTest(case=case["name"]):
                fingerprint_hash, version = _fingerprint(case)
                self.assertEqual(fingerprint_hash, case["expected_hash"])
                self.assertEqual(version, case["expected_version"])

    def test_drive_letter_is_observation_not_identity(self) -> None:
        original = self.cases["external_volume"]
        moved = self.cases["same_volume_changed_drive_letter"]
        replacement = self.cases["different_volume_same_drive_letter"]
        self.assertNotEqual(original["provider_native_root"], moved["provider_native_root"])
        self.assertEqual(_fingerprint(original), _fingerprint(moved))
        self.assertEqual(original["provider_native_root"], replacement["provider_native_root"])
        self.assertNotEqual(_fingerprint(original), _fingerprint(replacement))

    def test_optical_media_change_changes_v2_identity(self) -> None:
        stable = self.cases["optical_stable_media"]
        changed = self.cases["optical_changed_media"]
        self.assertNotEqual(_fingerprint(stable), _fingerprint(changed))

    def test_invalid_ambiguous_fixture_fails_closed(self) -> None:
        case = self.cases["invalid_ambiguous_drive_relative_root"]
        with self.assertRaisesRegex(ProviderNativePathError, case["expected_error"]):
            normalize_provider_native_root(case["provider_native_root"])

    def test_collector_runs_without_backend_service_imports(self) -> None:
        mapped_path = "Z:\\Family"
        canonical_path = "\\\\synthetic-nas\\photos\\Family"
        collector = WindowsIdentityCollector(
            command_runner=_FakeRunner(),
            path_probe=lambda path: PathProbeStatus(exists=True, is_dir=True, readable=True),
            mapped_drive_resolver=lambda path: canonical_path if path == mapped_path else None,
            command_timeout_seconds=0.01,
        )
        result = collector.collect(IdentityCollectionRequest(source_type="nas", observed_path=mapped_path))
        self.assertEqual(result.probe_status, "completed")
        self.assertEqual(result.source_root_candidate.path, canonical_path)
        self.assertIn("mapped_drive_unc_resolved", [item.code for item in result.evidence_items])
        self.assertFalse(any(name.startswith("app.services") for name in sys.modules))

        request = HelperProbeRequest(
            request_id=UUID("99999999-2222-4333-8444-555555555555"),
            source_type="nas",
            provider_native_path=ProviderNativePath(
                provider_native_root=mapped_path,
                provider_native_full_path=mapped_path,
            ),
            expected_collector_name="windows_non_admin_probe_v1",
            expected_collector_version="1",
        )
        wire_response = probe_response_from_collection(request=request, result=result)
        self.assertEqual(wire_response.result_status, "success")
        self.assertEqual(wire_response.collector_name, "windows_non_admin_probe_v1")


if __name__ == "__main__":
    unittest.main()
