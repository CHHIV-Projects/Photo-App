"""Tests for fail-closed YuNet artifact verification."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.provision_yunet_model import (
    MODEL_LICENSE,
    MODEL_SHA256,
    MODEL_SOURCE_URL,
    verify_model,
)


class YuNetProvisioningTests(unittest.TestCase):
    def test_manifest_records_authority_license_and_checksum(self) -> None:
        self.assertTrue(MODEL_SOURCE_URL.startswith("https://media.githubusercontent.com/"))
        self.assertIn("MIT", MODEL_LICENSE)
        self.assertEqual(len(MODEL_SHA256), 64)

    def test_verification_rejects_wrong_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "model.onnx"
            path.write_bytes(b"not the approved model")
            with self.assertRaisesRegex(ValueError, "size mismatch"):
                verify_model(path)


if __name__ == "__main__":
    unittest.main()
