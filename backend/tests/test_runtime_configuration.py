"""Focused tests for the Linux Development runtime configuration contract."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from app.core.config import settings
from app.core.runtime_paths import (
    StorageConfigurationError,
    configured_path,
    prepare_runtime_directories,
    reports_directory,
    resolve_runtime_path,
    validate_storage_configuration,
)


def _development_settings(root: Path, *, mode: str = "local"):
    return replace(
        settings,
        runtime_profile="development",
        storage_mode=mode,
        storage_root=str(root),
        vault_path=str(root / "vault"),
        drop_zone_path=str(root / "drop_zone"),
        quarantine_path=str(root / "quarantine"),
        ingest_failures_path=str(root / "ingest_failures"),
        previews_path=str(root / "previews"),
        thumbnails_path=str(root / "thumbnails"),
        review_path=str(root / "review"),
        logs_path=str(root / "logs"),
        reports_path=str(root / "reports"),
        exports_icloud_path=str(root / "exports" / "icloud"),
        model_cache_path=str(root / "models"),
        nas_mount_path=str(root),
        nas_environment_marker=".photo-organizer-environment",
        nas_environment_marker_value="environment=development",
    )


class RuntimeConfigurationTests(unittest.TestCase):
    def test_default_windows_development_storage_root_is_preserved(self) -> None:
        expected = (Path(__file__).resolve().parents[2] / "storage").resolve()
        self.assertEqual(resolve_runtime_path("../storage"), expected)

    def test_local_mode_creates_only_existing_startup_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "development"
            current = _development_settings(root)
            paths = prepare_runtime_directories(current)

            self.assertTrue(paths["vault_path"].is_dir())
            self.assertTrue(paths["previews_path"].is_dir())
            self.assertTrue(paths["review_path"].is_dir())
            self.assertFalse(paths["drop_zone_path"].exists())

    def test_development_rejects_production_path_segment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            current = _development_settings(Path(temporary) / "Production")
            with self.assertRaisesRegex(
                StorageConfigurationError,
                "cannot use a Production path",
            ):
                validate_storage_configuration(current)

    def test_invalid_storage_mode_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            current = _development_settings(Path(temporary), mode="automatic")
            with self.assertRaisesRegex(StorageConfigurationError, "local.*nas"):
                validate_storage_configuration(current)

    def test_nas_mode_requires_an_active_mount(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            current = _development_settings(root, mode="nas")
            with self.assertRaisesRegex(StorageConfigurationError, "not an active mount"):
                validate_storage_configuration(current, mount_checker=lambda _: False)

    def test_nas_mode_requires_exact_development_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            current = _development_settings(root, mode="nas")
            (root / ".photo-organizer-environment").write_text(
                "environment=production",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                StorageConfigurationError,
                "does not identify Development",
            ):
                validate_storage_configuration(current, mount_checker=lambda _: True)

    def test_nas_mode_has_no_local_fallback_and_requires_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            current = _development_settings(root, mode="nas")
            (root / ".photo-organizer-environment").write_text(
                "environment=development",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                StorageConfigurationError,
                "directories are missing",
            ):
                validate_storage_configuration(current, mount_checker=lambda _: True)
            self.assertFalse((root / "vault").exists())

    def test_valid_nas_contract_uses_only_preexisting_mount_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            current = _development_settings(root, mode="nas")
            (root / ".photo-organizer-environment").write_text(
                "environment=development",
                encoding="utf-8",
            )
            for field_name in (
                "vault_path",
                "drop_zone_path",
                "quarantine_path",
                "ingest_failures_path",
                "previews_path",
                "thumbnails_path",
                "review_path",
                "logs_path",
                "reports_path",
                "exports_icloud_path",
                "model_cache_path",
            ):
                Path(getattr(current, field_name)).mkdir(parents=True, exist_ok=True)

            paths = validate_storage_configuration(
                current,
                mount_checker=lambda _: True,
            )
            self.assertEqual(paths["storage_root"], root.resolve())
            self.assertEqual(
                reports_directory("run", current_settings=current),
                (root / "reports" / "run").resolve(),
            )
            self.assertEqual(
                configured_path("previews_path", current_settings=current),
                (root / "previews").resolve(),
            )


if __name__ == "__main__":
    unittest.main()
