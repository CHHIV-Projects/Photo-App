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

    def test_local_mode_creates_only_authorized_startup_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "development"
            current = _development_settings(root)
            paths = prepare_runtime_directories(current)

            expected_created = {
                "vault_path",
                "drop_zone_path",
                "previews_path",
                "review_path",
            }
            for field_name in expected_created:
                self.assertTrue(paths[field_name].is_dir())

            expected_unmanaged = {
                "quarantine_path",
                "ingest_failures_path",
                "thumbnails_path",
                "logs_path",
                "reports_path",
                "exports_icloud_path",
                "model_cache_path",
            }
            for field_name in expected_unmanaged:
                self.assertFalse(paths[field_name].exists())

            created_fields = {
                field_name
                for field_name in expected_created | expected_unmanaged
                if paths[field_name].is_dir()
            }
            self.assertEqual(created_fields, expected_created)

    def test_local_mode_startup_is_idempotent_and_preserves_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "development"
            current = _development_settings(root)
            expected_created = (
                "vault_path",
                "drop_zone_path",
                "previews_path",
                "review_path",
            )
            sentinels: dict[str, Path] = {}

            for field_name in expected_created:
                directory = Path(getattr(current, field_name))
                directory.mkdir(parents=True, exist_ok=True)
                sentinel = directory / f"{field_name}.sentinel"
                sentinel.write_bytes(f"preserve:{field_name}".encode("utf-8"))
                sentinels[field_name] = sentinel

            before = {
                field_name: (
                    sentinel.read_bytes(),
                    sentinel.stat().st_size,
                    sentinel.stat().st_mtime_ns,
                )
                for field_name, sentinel in sentinels.items()
            }

            first_paths = prepare_runtime_directories(current)
            second_paths = prepare_runtime_directories(current)

            self.assertEqual(first_paths, second_paths)
            for field_name, sentinel in sentinels.items():
                self.assertTrue(first_paths[field_name].is_dir())
                self.assertTrue(sentinel.is_file())
                self.assertEqual(
                    (
                        sentinel.read_bytes(),
                        sentinel.stat().st_size,
                        sentinel.stat().st_mtime_ns,
                    ),
                    before[field_name],
                )

    def test_test_and_production_profiles_do_not_create_runtime_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            for runtime_profile in ("test", "production"):
                with self.subTest(runtime_profile=runtime_profile):
                    root = temporary_root / f"{runtime_profile}-runtime"
                    current = replace(
                        _development_settings(root),
                        runtime_profile=runtime_profile,
                    )

                    paths = prepare_runtime_directories(current)

                    self.assertFalse(root.exists())
                    self.assertFalse(paths["drop_zone_path"].exists())

    def test_unusable_configured_drop_zone_fails_without_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            root = temporary_root / "development"
            blocked_parent = temporary_root / "blocked-parent"
            blocked_parent.write_text("not a directory", encoding="utf-8")
            configured_drop_zone = blocked_parent / "configured-drop-zone"
            current = replace(
                _development_settings(root),
                drop_zone_path=str(configured_drop_zone),
            )

            with self.assertRaisesRegex(
                StorageConfigurationError,
                "drop_zone_path",
            ):
                prepare_runtime_directories(current)

            self.assertFalse(configured_drop_zone.exists())
            self.assertFalse((root / "drop_zone").exists())

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
            self.assertFalse((root / "drop_zone").exists())

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
