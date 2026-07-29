from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "fixtures"
    / "create_controlled_photo_fixture_set.py"
)
SPEC = importlib.util.spec_from_file_location(
    "create_controlled_photo_fixture_set",
    SCRIPT_PATH,
)
assert SPEC is not None and SPEC.loader is not None
fixture_generator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = fixture_generator
SPEC.loader.exec_module(fixture_generator)


LIVE_MINIMUM_FILE_SIZE_BYTES = 51_200
EXPECTED_FILENAMES = {
    "unique_a.jpg",
    "unique_a_duplicate.jpg",
    "unique_b.jpg",
    "preview_source.tiff",
}


class ControlledPhotoFixtureGeneratorTests(unittest.TestCase):
    def test_two_independent_generations_are_byte_for_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            first = base / "fixture_a"
            second = base / "fixture_b"

            first_manifest = fixture_generator.create_controlled_fixture_set(
                fixture_root=first,
                minimum_file_size_bytes=LIVE_MINIMUM_FILE_SIZE_BYTES,
            )
            second_manifest = fixture_generator.create_controlled_fixture_set(
                fixture_root=second,
                minimum_file_size_bytes=LIVE_MINIMUM_FILE_SIZE_BYTES,
            )

            self.assertEqual(first_manifest, second_manifest)
            for relative_path in fixture_generator.MANAGED_RELATIVE_PATHS:
                self.assertEqual(
                    (first / relative_path).read_bytes(),
                    (second / relative_path).read_bytes(),
                )

    def test_manifest_hashes_sizes_dimensions_metadata_and_totals_match_files(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "fixture"
            manifest = fixture_generator.create_controlled_fixture_set(
                fixture_root=root,
                minimum_file_size_bytes=LIVE_MINIMUM_FILE_SIZE_BYTES,
            )

            manifest_on_disk = json.loads(
                (root / fixture_generator.MANIFEST_FILENAME).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(manifest, manifest_on_disk)
            self.assertTrue(manifest["no_personal_media"])
            self.assertEqual(
                manifest["effective_minimum_file_size_bytes"],
                LIVE_MINIMUM_FILE_SIZE_BYTES,
            )
            self.assertEqual(
                manifest["required_media_size_with_margin_bytes"],
                LIVE_MINIMUM_FILE_SIZE_BYTES
                + fixture_generator.MINIMUM_SIZE_MARGIN_BYTES,
            )
            self.assertEqual(
                manifest["expected_totals"],
                {
                    "source_filenames": 4,
                    "unique_hashes": 3,
                    "assets": 3,
                    "vault_objects": 3,
                    "provenance_observations": 4,
                    "tiff_preview_eligible": 1,
                },
            )

            entries = {
                entry["filename"]: entry for entry in manifest["files"]
            }
            self.assertEqual(set(entries), EXPECTED_FILENAMES)
            for filename, entry in entries.items():
                path = root / entry["relative_path"]
                payload = path.read_bytes()
                self.assertEqual(entry["sha256"], sha256(payload).hexdigest())
                self.assertEqual(entry["byte_size"], len(payload))
                self.assertGreater(
                    len(payload),
                    manifest["required_media_size_with_margin_bytes"],
                )

                with Image.open(path) as image:
                    self.assertEqual(
                        image.size,
                        (
                            entry["dimensions"]["width"],
                            entry["dimensions"]["height"],
                        ),
                    )
                    exif = image.getexif()
                    metadata = entry["controlled_metadata"]
                    self.assertEqual(exif.get(270), metadata["ImageDescription"])
                    self.assertEqual(exif.get(271), metadata["Make"])
                    self.assertEqual(exif.get(272), metadata["Model"])
                    self.assertEqual(exif.get(305), metadata["Software"])
                    self.assertEqual(exif.get(306), metadata["DateTime"])
                    if filename.endswith(".jpg"):
                        self.assertEqual(
                            exif.get(36867),
                            metadata["DateTimeOriginal"],
                        )
                        self.assertEqual(
                            exif.get(36868),
                            metadata["DateTimeDigitized"],
                        )

    def test_exact_duplicate_and_unique_hash_relationships_are_correct(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "fixture"
            manifest = fixture_generator.create_controlled_fixture_set(
                fixture_root=root,
                minimum_file_size_bytes=LIVE_MINIMUM_FILE_SIZE_BYTES,
            )
            entries = {
                entry["filename"]: entry for entry in manifest["files"]
            }

            unique_a = root / "source" / "unique_a.jpg"
            duplicate = root / "source" / "unique_a_duplicate.jpg"
            unique_b = root / "source" / "unique_b.jpg"
            tiff = root / "source" / "preview_source.tiff"

            self.assertEqual(unique_a.read_bytes(), duplicate.read_bytes())
            self.assertEqual(
                entries["unique_a_duplicate.jpg"]["exact_duplicate_of"],
                "unique_a.jpg",
            )
            self.assertEqual(
                entries["unique_a.jpg"]["sha256"],
                entries["unique_a_duplicate.jpg"]["sha256"],
            )
            self.assertEqual(
                len(
                    {
                        sha256(path.read_bytes()).hexdigest()
                        for path in (unique_a, duplicate, unique_b, tiff)
                    }
                ),
                3,
            )

    def test_generation_produces_only_the_expected_managed_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "fixture"
            fixture_generator.create_controlled_fixture_set(
                fixture_root=root,
                minimum_file_size_bytes=LIVE_MINIMUM_FILE_SIZE_BYTES,
            )

            actual = {
                path.relative_to(root)
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(
                actual,
                set(fixture_generator.MANAGED_RELATIVE_PATHS),
            )
            self.assertEqual(
                {
                    path.name
                    for path in (root / "source").iterdir()
                    if path.is_file()
                },
                EXPECTED_FILENAMES,
            )

    def test_unknown_existing_content_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "fixture"
            root.mkdir()
            unknown = root / "unknown.txt"
            unknown.write_text("preserve me", encoding="utf-8")

            with self.assertRaises(fixture_generator.FixtureGenerationError):
                fixture_generator.create_controlled_fixture_set(
                    fixture_root=root,
                    minimum_file_size_bytes=LIVE_MINIMUM_FILE_SIZE_BYTES,
                )

            self.assertEqual(unknown.read_text(encoding="utf-8"), "preserve me")
            self.assertFalse((root / "source").exists())

    def test_known_override_file_is_preserved_but_not_managed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "fixture"
            source = root / "source"
            source.mkdir(parents=True)
            override = root / fixture_generator.APPROVED_BOUNDARY_FILENAME
            override_payload = "services:\n  backend: {}\n"
            override.write_text(override_payload, encoding="utf-8")

            fixture_generator.create_controlled_fixture_set(
                fixture_root=root,
                minimum_file_size_bytes=LIVE_MINIMUM_FILE_SIZE_BYTES,
            )

            self.assertEqual(
                override.read_text(encoding="utf-8"),
                override_payload,
            )
            self.assertNotIn(
                Path(fixture_generator.APPROVED_BOUNDARY_FILENAME),
                fixture_generator.MANAGED_RELATIVE_PATHS,
            )

    def test_existing_managed_set_requires_explicit_safe_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "fixture"
            original = fixture_generator.create_controlled_fixture_set(
                fixture_root=root,
                minimum_file_size_bytes=LIVE_MINIMUM_FILE_SIZE_BYTES,
            )

            with self.assertRaises(fixture_generator.FixtureGenerationError):
                fixture_generator.create_controlled_fixture_set(
                    fixture_root=root,
                    minimum_file_size_bytes=LIVE_MINIMUM_FILE_SIZE_BYTES,
                )

            replaced = fixture_generator.create_controlled_fixture_set(
                fixture_root=root,
                minimum_file_size_bytes=LIVE_MINIMUM_FILE_SIZE_BYTES,
                replace_known=True,
            )
            self.assertEqual(original, replaced)

    def test_tampered_managed_set_cannot_be_safely_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "fixture"
            fixture_generator.create_controlled_fixture_set(
                fixture_root=root,
                minimum_file_size_bytes=LIVE_MINIMUM_FILE_SIZE_BYTES,
            )
            tampered = root / "source" / "unique_a.jpg"
            tampered.write_bytes(b"tampered")

            with self.assertRaises(fixture_generator.FixtureGenerationError):
                fixture_generator.create_controlled_fixture_set(
                    fixture_root=root,
                    minimum_file_size_bytes=LIVE_MINIMUM_FILE_SIZE_BYTES,
                    replace_known=True,
                )

            self.assertEqual(tampered.read_bytes(), b"tampered")

    def test_unsafe_roots_and_invalid_thresholds_are_rejected(self) -> None:
        assert fixture_generator.REPOSITORY_ROOT is not None
        unsafe_roots = [
            "relative/fixture",
            str(Path(Path.cwd().anchor)),
            str(fixture_generator.REPOSITORY_ROOT),
            str(fixture_generator.REPOSITORY_ROOT / "fixture"),
            str(fixture_generator.REPOSITORY_ROOT / "storage" / "fixture"),
            str(Path(tempfile.gettempdir()) / "production" / "fixture"),
            str(Path(tempfile.gettempdir()) / "production-fixtures" / "fixture"),
            str(Path(tempfile.gettempdir()) / "tests" / "fixture"),
            str(Path(tempfile.gettempdir()) / "m005-test" / "fixture"),
            str(Path(Path.cwd().anchor) / "mnt" / "nas" / "fixture"),
            str(Path(Path.cwd().anchor) / "app" / "storage" / "fixture"),
        ]
        for unsafe_root in unsafe_roots:
            with self.subTest(unsafe_root=unsafe_root):
                with self.assertRaises(
                    fixture_generator.FixtureGenerationError
                ):
                    fixture_generator.create_controlled_fixture_set(
                        fixture_root=unsafe_root,
                        minimum_file_size_bytes=LIVE_MINIMUM_FILE_SIZE_BYTES,
                    )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "fixture"
            for invalid_threshold in (0, -1, True):
                with self.subTest(invalid_threshold=invalid_threshold):
                    with self.assertRaises(
                        fixture_generator.FixtureGenerationError
                    ):
                        fixture_generator.create_controlled_fixture_set(
                            fixture_root=root,
                            minimum_file_size_bytes=invalid_threshold,
                        )

    def test_threshold_that_payloads_cannot_safely_exceed_writes_nothing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "fixture"
            with self.assertRaises(fixture_generator.FixtureGenerationError):
                fixture_generator.create_controlled_fixture_set(
                    fixture_root=root,
                    minimum_file_size_bytes=100_000_000,
                )
            self.assertFalse(root.exists())

    def test_symlink_component_is_rejected_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "fixture"
            with patch.object(
                fixture_generator,
                "_path_has_symlink_component",
                return_value=True,
            ):
                with self.assertRaises(
                    fixture_generator.FixtureGenerationError
                ):
                    fixture_generator.create_controlled_fixture_set(
                        fixture_root=root,
                        minimum_file_size_bytes=LIVE_MINIMUM_FILE_SIZE_BYTES,
                    )
            self.assertFalse(root.exists())

    def test_real_directory_symlink_escape_is_rejected_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            outside = base / "outside"
            outside.mkdir()
            root = base / "fixture"
            try:
                root.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"Directory symlinks are unavailable: {exc}")

            with self.assertRaises(fixture_generator.FixtureGenerationError):
                fixture_generator.create_controlled_fixture_set(
                    fixture_root=root,
                    minimum_file_size_bytes=LIVE_MINIMUM_FILE_SIZE_BYTES,
                )
            self.assertEqual(list(outside.iterdir()), [])

    def test_generation_requires_no_network_or_external_service(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "fixture"
            with patch.object(
                socket,
                "socket",
                side_effect=AssertionError("network access is not allowed"),
            ):
                fixture_generator.create_controlled_fixture_set(
                    fixture_root=root,
                    minimum_file_size_bytes=LIVE_MINIMUM_FILE_SIZE_BYTES,
                )

            self.assertTrue((root / fixture_generator.MANIFEST_FILENAME).is_file())


if __name__ == "__main__":
    unittest.main()
