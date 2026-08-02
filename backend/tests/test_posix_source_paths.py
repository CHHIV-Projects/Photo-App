"""Dependency-free focused POSIX Source mapping tests."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "app/services/source_identity/posix_source_paths.py"
SPEC = importlib.util.spec_from_file_location("posix_source_paths", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class PosixSourcePathTests(unittest.TestCase):
    def test_contained_mapping_separates_host_and_runtime_roots(self) -> None:
        mapping = module.map_configured_slot(
            host_slot="/mnt/photo-organizer-sources/local/server-photos",
            runtime_slot="/app/sources/local/server-photos",
            relative_root="family/photos",
        )
        self.assertEqual(mapping.host_observed_path, "/mnt/photo-organizer-sources/local/server-photos/family/photos")
        self.assertEqual(mapping.runtime_root, "/app/sources/local/server-photos/family/photos")
        self.assertEqual(mapping.relative_root, "family/photos")

    def test_absolute_traversal_empty_components_and_root_slots_fail(self) -> None:
        for relative in ("/etc", "../etc", "family/../etc", "family//photos", "./family"):
            with self.subTest(relative=relative), self.assertRaises(module.PosixSourcePathError):
                module.map_configured_slot(
                    host_slot="/mnt/photo-organizer-sources/local/server-photos",
                    runtime_slot="/app/sources/local/server-photos",
                    relative_root=relative,
                )
        with self.assertRaises(module.PosixSourcePathError):
            module.map_configured_slot(host_slot="/", runtime_slot="/app/sources/local/server-photos", relative_root="")

    def test_exact_mapping_rejects_root_substitution(self) -> None:
        with self.assertRaisesRegex(module.PosixSourcePathError, "Observed Path"):
            module.require_exact_mapping(
                host_slot="/mnt/photo-organizer-sources/nas/photo-organizer",
                runtime_slot="/app/sources/nas/photo-organizer",
                relative_root="family",
                host_observed_path="/mnt/nas/photo-organizer/family",
                runtime_root="/app/sources/nas/photo-organizer/family",
            )
        with self.assertRaisesRegex(module.PosixSourcePathError, "Runtime Root"):
            module.require_exact_mapping(
                host_slot="/mnt/photo-organizer-sources/nas/photo-organizer",
                runtime_slot="/app/sources/nas/photo-organizer",
                relative_root="family",
                host_observed_path="/mnt/photo-organizer-sources/nas/photo-organizer/family",
                runtime_root="/app/storage/family",
            )


if __name__ == "__main__":
    unittest.main()
