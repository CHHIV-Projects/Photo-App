from __future__ import annotations

import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.source_identity.probe_schema import SourceIdentityProbeRequest


class SourceIdentityProbeSchemaTests(unittest.TestCase):
    def test_probe_request_defaults_include_raw_evidence_false(self) -> None:
        request = SourceIdentityProbeRequest(source_type="external_device", observed_path="E:\\Photos")

        self.assertEqual(request.probe_mode, "setup_probe")
        self.assertEqual(request.os_family, "unknown")
        self.assertFalse(request.include_raw_evidence)

    def test_valid_source_types_are_accepted(self) -> None:
        for source_type in ("local", "external_device", "removable_media", "nas", "cloud"):
            with self.subTest(source_type=source_type):
                request = SourceIdentityProbeRequest(source_type=source_type, observed_path="C:\\")
                self.assertEqual(request.source_type, source_type)

    def test_invalid_source_type_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            SourceIdentityProbeRequest(source_type="external_drive", observed_path="E:\\")

    def test_valid_probe_modes_are_accepted(self) -> None:
        for mode in ("setup_probe", "readiness_probe", "run_launch_verification", "diagnostic_probe"):
            with self.subTest(mode=mode):
                request = SourceIdentityProbeRequest(source_type="local", observed_path="C:\\", probe_mode=mode)
                self.assertEqual(request.probe_mode, mode)

    def test_invalid_probe_mode_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            SourceIdentityProbeRequest(source_type="local", observed_path="C:\\", probe_mode="run_now")


if __name__ == "__main__":
    unittest.main()
