from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.source_identity.probe_schema import SourceIdentityProbeRequest
from app.services.source_identity.providers.base import CommandResult
from app.services.source_identity.providers.windows_non_admin import (
    PathProbeStatus,
    WindowsSourceIdentityProbeProvider,
    mask_guid,
    mask_identifier,
)


class _FakeCommandRunner:
    def __init__(self, results: dict[tuple[str, ...], CommandResult] | None = None) -> None:
        self.results = results or {}
        self.calls: list[tuple[str, ...]] = []

    def run(self, args: list[str], *, timeout_seconds: float) -> CommandResult:
        key = tuple(args)
        self.calls.append(key)
        return self.results.get(key, CommandResult(args=key, returncode=0, stdout=""))


def _path_probe(readable_paths: set[str], *, access_denied_paths: set[str] | None = None):
    access_denied_paths = access_denied_paths or set()

    def _probe(path: str | None) -> PathProbeStatus:
        if path in access_denied_paths:
            return PathProbeStatus(exists=True, is_dir=True, readable=False, access_denied=True)
        if path in readable_paths:
            return PathProbeStatus(exists=True, is_dir=True, readable=True)
        return PathProbeStatus(exists=False, is_dir=False, readable=False)

    return _probe


def _provider(
    *,
    readable_paths: set[str] | None = None,
    access_denied_paths: set[str] | None = None,
    results: dict[tuple[str, ...], CommandResult] | None = None,
) -> WindowsSourceIdentityProbeProvider:
    return WindowsSourceIdentityProbeProvider(
        command_runner=_FakeCommandRunner(results),
        path_probe=_path_probe(readable_paths or set(), access_denied_paths=access_denied_paths),
        command_timeout_seconds=0.01,
    )


class WindowsSourceIdentityProbeProviderTests(unittest.TestCase):
    def test_source_root_classification_by_source_type(self) -> None:
        cases = [
            ("local", "C:\\", "local_volume_root"),
            ("local", "C:\\Photos", "local_folder"),
            ("external_device", "F:\\", "external_volume_root"),
            ("external_device", "F:\\Photos", "external_folder"),
            ("removable_media", "H:\\", "removable_media_root"),
            ("removable_media", "H:\\DCIM", "removable_media_folder"),
            ("nas", "\\\\HENDERSON-NAS", "nas_server_only"),
            ("nas", "\\\\HENDERSON-NAS\\Photos", "nas_share_root"),
            ("nas", "\\\\HENDERSON-NAS\\Photos\\Family Archive", "nas_share_folder"),
        ]
        readable_paths = {path for _, path, boundary in cases if boundary != "nas_server_only"}
        provider = _provider(readable_paths=readable_paths)

        for source_type, path, boundary in cases:
            with self.subTest(source_type=source_type, path=path):
                response = provider.probe(SourceIdentityProbeRequest(source_type=source_type, observed_path=path))
                self.assertEqual(response.source_root_candidate.filesystem_boundary_type, boundary)

    def test_nas_server_only_blocks_as_not_runnable(self) -> None:
        provider = _provider()

        response = provider.probe(
            SourceIdentityProbeRequest(source_type="nas", observed_path="\\\\HENDERSON-NAS")
        )

        self.assertEqual(response.source_root_candidate.filesystem_boundary_type, "nas_server_only")
        self.assertFalse(response.source_root_candidate.is_valid_source_root_candidate)
        self.assertFalse(response.safe_to_run)
        self.assertIn("nas_server_not_runnable", [item.code for item in response.blockers])

    def test_nas_share_and_folder_are_valid_when_readable(self) -> None:
        paths = {"\\\\HENDERSON-NAS\\Photos", "\\\\HENDERSON-NAS\\Photos\\Family Archive"}
        provider = _provider(readable_paths=paths)

        share_response = provider.probe(
            SourceIdentityProbeRequest(source_type="nas", observed_path="\\\\HENDERSON-NAS\\Photos")
        )
        folder_response = provider.probe(
            SourceIdentityProbeRequest(source_type="nas", observed_path="\\\\HENDERSON-NAS\\Photos\\Family Archive")
        )

        self.assertEqual(share_response.source_root_candidate.filesystem_boundary_type, "nas_share_root")
        self.assertTrue(share_response.source_root_candidate.is_valid_source_root_candidate)
        self.assertEqual(folder_response.source_root_candidate.filesystem_boundary_type, "nas_share_folder")
        self.assertTrue(folder_response.source_root_candidate.is_valid_source_root_candidate)

    def test_unreadable_nas_path_returns_access_blocker(self) -> None:
        path = "\\\\HENDERSON-NAS\\Photos"
        provider = _provider(access_denied_paths={path})

        response = provider.probe(SourceIdentityProbeRequest(source_type="nas", observed_path=path))

        self.assertFalse(response.safe_to_run)
        self.assertIn("access_denied", [item.code for item in response.blockers])

    def test_external_partial_evidence_needs_review_and_masks_raw_values(self) -> None:
        results = {
            ("cmd", "/c", "vol", "E:"): CommandResult(
                args=("cmd", "/c", "vol", "E:"),
                returncode=0,
                stdout="Volume Serial Number is 1234-ABCD",
            ),
            ("cmd", "/c", "mountvol", "E:", "/L"): CommandResult(
                args=("cmd", "/c", "mountvol", "E:", "/L"),
                returncode=0,
                stdout="\\\\?\\Volume{12345678-90AB-CDEF-1234-567890ABCDEF}\\",
            ),
            ("cmd", "/c", "fsutil", "fsinfo", "drivetype", "E:"): CommandResult(
                args=("cmd", "/c", "fsutil", "fsinfo", "drivetype", "E:"),
                returncode=0,
                stdout="E: - Fixed Drive",
            ),
        }
        provider = _provider(readable_paths={"E:\\Photos"}, results=results)

        response = provider.probe(
            SourceIdentityProbeRequest(source_type="external_device", observed_path="E:\\Photos")
        )
        payload = response.model_dump_json()

        self.assertEqual(response.safe_to_run, "needs_review")
        self.assertIn(response.confidence_tier, {"medium_needs_review", "weak_manual_confirmation_required"})
        self.assertNotIn("1234-ABCD", payload)
        self.assertNotIn("12345678-90AB-CDEF-1234-567890ABCDEF", payload)
        self.assertIn("volume_serial_present", [item.code for item in response.evidence_items])
        self.assertIn("volume_guid_present", [item.code for item in response.evidence_items])

    def test_command_failures_are_summarized_not_crashes(self) -> None:
        results = {
            ("cmd", "/c", "vol", "C:"): CommandResult(
                args=("cmd", "/c", "vol", "C:"),
                returncode=1,
                stderr="Access is denied.",
            ),
            ("cmd", "/c", "mountvol", "C:", "/L"): CommandResult(
                args=("cmd", "/c", "mountvol", "C:", "/L"),
                returncode=None,
                command_not_found=True,
            ),
            ("cmd", "/c", "fsutil", "fsinfo", "drivetype", "C:"): CommandResult(
                args=("cmd", "/c", "fsutil", "fsinfo", "drivetype", "C:"),
                returncode=None,
                timed_out=True,
            ),
            ("cmd", "/c", "fsutil", "fsinfo", "volumeinfo", "C:"): CommandResult(
                args=("cmd", "/c", "fsutil", "fsinfo", "volumeinfo", "C:"),
                returncode=2,
                stderr="Unexpected non-zero exit.",
            ),
        }
        provider = _provider(readable_paths={"C:\\Photos"}, results=results)

        response = provider.probe(SourceIdentityProbeRequest(source_type="local", observed_path="C:\\Photos"))
        warning_codes = {item.code for item in response.warnings}

        self.assertIn("command_access_denied", warning_codes)
        self.assertIn("command_unavailable", warning_codes)
        self.assertIn("command_timeout", warning_codes)
        self.assertIn("command_nonzero_exit", warning_codes)
        self.assertIn(response.probe_status, {"completed_with_warnings", "completed"})

    def test_cloud_probe_does_not_probe_provider_credentials(self) -> None:
        runner = _FakeCommandRunner()
        provider = WindowsSourceIdentityProbeProvider(
            command_runner=runner,
            path_probe=_path_probe(set()),
            command_timeout_seconds=0.01,
        )

        response = provider.probe(SourceIdentityProbeRequest(source_type="cloud", observed_path=None))

        self.assertEqual(response.safe_to_run, "not_applicable")
        self.assertIn("cloud_provider_not_probeable", [item.code for item in response.warnings])
        self.assertEqual(runner.calls, [])

    def test_mask_helpers_do_not_return_full_identifiers(self) -> None:
        self.assertEqual(mask_identifier("ABCDEFG123456"), "...3456")
        self.assertEqual(mask_guid("Volume{12345678-90AB-CDEF-1234-567890ABCDEF}"), "{...cdef}")


if __name__ == "__main__":
    unittest.main()
