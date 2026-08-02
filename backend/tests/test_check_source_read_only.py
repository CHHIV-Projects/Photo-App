"""Focused tests for the non-mutating Source read-only validation helper."""

from __future__ import annotations

import errno
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[2] / "scripts/operator/linux/check_source_read_only.py"
SPEC = importlib.util.spec_from_file_location("check_source_read_only", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class CheckSourceReadOnlyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "folder").mkdir()
        self.file = self.root / "folder" / "probe.bin"
        self.file.write_bytes(b"unchanged")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _open_error(self, error_number: int) -> str:
        with patch.object(module.os, "open", side_effect=OSError(error_number, "bounded")) as mocked:
            result = module.check_existing_file(self.root, "folder/probe.bin")
        mocked.assert_called_once_with(self.file, os.O_WRONLY | os.O_CLOEXEC)
        return result

    def test_erofs_is_the_only_read_only_proof(self) -> None:
        self.assertEqual(self._open_error(errno.EROFS), "READ_ONLY_EROFS")

    def test_permission_denials_are_reported_separately(self) -> None:
        self.assertEqual(
            self._open_error(errno.EACCES),
            "PERMISSION_DENIED_NOT_READ_ONLY_PROOF",
        )
        self.assertEqual(
            self._open_error(errno.EPERM),
            "PERMISSION_DENIED_NOT_READ_ONLY_PROOF",
        )

    def test_successful_write_open_closes_without_writing_or_truncating(self) -> None:
        with (
            patch.object(module.os, "open", return_value=73) as opened,
            patch.object(module.os, "close") as closed,
        ):
            result = module.check_existing_file(self.root, "folder/probe.bin")
        opened.assert_called_once_with(self.file, os.O_WRONLY | os.O_CLOEXEC)
        closed.assert_called_once_with(73)
        self.assertEqual(result, "WRITE_OPEN_SUCCEEDED")
        self.assertEqual(self.file.read_bytes(), b"unchanged")

    def test_unexpected_open_errno_blocks(self) -> None:
        self.assertEqual(self._open_error(errno.EIO), "UNEXPECTED_OPEN_ERROR")

    def test_missing_directory_symlink_and_escape_block_before_open(self) -> None:
        (self.root / "directory").mkdir()
        (self.root / "link").symlink_to(self.file)
        cases = (
            ("missing.bin", "FILE_MISSING"),
            ("directory", "NOT_REGULAR_FILE"),
            ("link", "SYMLINK_REJECTED"),
            ("../outside.bin", "PATH_INVALID"),
            ("/absolute.bin", "PATH_INVALID"),
        )
        for relative_value, result_class in cases:
            with self.subTest(relative_value=relative_value):
                with self.assertRaisesRegex(module.ProbeBlocked, result_class):
                    module.check_existing_file(self.root, relative_value)


if __name__ == "__main__":
    unittest.main()
