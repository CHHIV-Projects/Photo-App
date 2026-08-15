from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "app"))

from windows_helper_shared.paths import (  # noqa: E402
    ProviderNativePathError,
    normalize_provider_native_relative_path,
    normalize_provider_native_root,
    reconstruct_provider_native_full_path,
    validate_provider_native_path,
)


class ProviderNativePathTests(unittest.TestCase):
    def test_drive_and_unc_roots_remain_windows_native(self) -> None:
        self.assertEqual(normalize_provider_native_root("c:/Photos/Family"), "c:\\Photos\\Family")
        self.assertEqual(
            normalize_provider_native_root("//SERVER/Share/Family"),
            "\\\\SERVER\\Share\\Family",
        )

    def test_relative_and_full_path_reconstruct_exactly(self) -> None:
        relative = normalize_provider_native_relative_path("2025/Trip/image.jpg")
        full_path = reconstruct_provider_native_full_path("E:\\Photos", relative)
        self.assertEqual(relative, "2025\\Trip\\image.jpg")
        self.assertEqual(full_path, "E:\\Photos\\2025\\Trip\\image.jpg")
        self.assertEqual(
            validate_provider_native_path("E:\\Photos", relative, full_path),
            ("E:\\Photos", relative, full_path),
        )
        self.assertNotIn("/", full_path)

    def test_empty_relative_path_represents_exact_root(self) -> None:
        self.assertEqual(reconstruct_provider_native_full_path("R:\\DCIM", ""), "R:\\DCIM")

    def test_parent_and_cross_volume_escape_fail_closed(self) -> None:
        with self.assertRaises(ProviderNativePathError):
            reconstruct_provider_native_full_path("E:\\Photos", "..\\Secrets")
        with self.assertRaises(ProviderNativePathError):
            validate_provider_native_path("E:\\Photos", "Family", "F:\\Photos\\Family")

    def test_drive_relative_device_namespace_and_ambiguous_forms_fail(self) -> None:
        for value in ("C:Photos", "\\\\?\\C:\\Photos", "C:\\Photos.\\Family"):
            with self.subTest(value=value), self.assertRaises(ProviderNativePathError):
                normalize_provider_native_root(value)

    def test_absolute_or_ads_relative_paths_fail(self) -> None:
        for value in ("C:\\Elsewhere", "\\\\server\\share", "image.jpg:stream"):
            with self.subTest(value=value), self.assertRaises(ProviderNativePathError):
                normalize_provider_native_relative_path(value)


if __name__ == "__main__":
    unittest.main()
