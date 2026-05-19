from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.icloud_acquisition.known_state_service import (
    CAUGHT_UP_LIKELY,
    CAUGHT_UP_PARTIAL,
    CAUGHT_UP_UNKNOWN,
    KNOWN_STATE_STAGED,
    KNOWN_STATE_VAULT_VERIFIED,
    PreflightCandidate,
    derive_caught_up_status,
    evaluate_known_state,
    parse_preflight_candidates,
)


class _ExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class IcloudKnownStateServiceTests(unittest.TestCase):
    def test_parse_preflight_candidates_preserves_unknown_lines(self) -> None:
        stdout = "2026/05/IMG_0001.HEIC\nINFO Downloading\nIMG_0002.MOV\nMALFORMED_LINE"
        candidates = parse_preflight_candidates(stdout, None)

        self.assertEqual(len(candidates), 3)
        self.assertFalse(candidates[0].unknown_identity)
        self.assertEqual(candidates[0].normalized_source_relative_path, "2026/05/IMG_0001.HEIC")
        self.assertFalse(candidates[1].unknown_identity)
        self.assertEqual(candidates[1].normalized_source_relative_path, "IMG_0002.MOV")
        self.assertTrue(candidates[2].unknown_identity)
        self.assertIsNone(candidates[2].normalized_source_relative_path)

    def test_derive_caught_up_status_conservative_rules(self) -> None:
        self.assertEqual(
            derive_caught_up_status(
                preflight_ok=True,
                preflight_candidate_count=3,
                unknown_identity_count=0,
                all_candidates_already_known=True,
                download_skipped_due_to_all_known=True,
            ),
            CAUGHT_UP_LIKELY,
        )
        self.assertEqual(
            derive_caught_up_status(
                preflight_ok=True,
                preflight_candidate_count=3,
                unknown_identity_count=1,
                all_candidates_already_known=True,
                download_skipped_due_to_all_known=True,
            ),
            CAUGHT_UP_PARTIAL,
        )
        self.assertEqual(
            derive_caught_up_status(
                preflight_ok=False,
                preflight_candidate_count=3,
                unknown_identity_count=0,
                all_candidates_already_known=False,
                download_skipped_due_to_all_known=False,
            ),
            CAUGHT_UP_UNKNOWN,
        )

    def test_evaluate_known_state_staged_only_not_already_known(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            staging_root = Path(temp_dir)
            relative = Path("2026/05/IMG_0003.HEIC")
            full_path = staging_root / relative
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text("x", encoding="utf-8")

            candidate = PreflightCandidate(
                raw_line=str(relative).replace("\\", "/"),
                normalized_source_relative_path=str(relative).replace("\\", "/"),
                unknown_identity=False,
            )

            db_session = MagicMock()
            db_session.execute.return_value = _ExecuteResult([])

            summary = evaluate_known_state(
                db_session,
                ingestion_source_id=123,
                staging_root=staging_root,
                candidates=[candidate],
            )

            self.assertEqual(summary.candidate_count, 1)
            self.assertEqual(summary.staged_known_count, 1)
            self.assertEqual(summary.already_known_count, 0)
            self.assertEqual(summary.candidates[0].known_state, KNOWN_STATE_STAGED)

    def test_evaluate_known_state_vault_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            staging_root = Path(temp_dir)
            relative_path = "2026/05/IMG_0004.HEIC"
            candidate = PreflightCandidate(
                raw_line=relative_path,
                normalized_source_relative_path=relative_path,
                unknown_identity=False,
            )

            vault_file = staging_root / "vault" / "asset.heic"
            vault_file.parent.mkdir(parents=True, exist_ok=True)
            vault_file.write_text("x", encoding="utf-8")

            provenance = SimpleNamespace(asset_sha256="abc123", source_relative_path=relative_path)
            asset = SimpleNamespace(sha256="abc123", vault_path=str(vault_file))

            db_session = MagicMock()
            db_session.execute.side_effect = [
                _ExecuteResult([provenance]),
                _ExecuteResult([asset]),
            ]

            summary = evaluate_known_state(
                db_session,
                ingestion_source_id=123,
                staging_root=staging_root,
                candidates=[candidate],
            )

            self.assertEqual(summary.already_known_count, 1)
            self.assertEqual(summary.vault_verified_known_count, 1)
            self.assertEqual(summary.candidates[0].known_state, KNOWN_STATE_VAULT_VERIFIED)

    def test_parse_preflight_candidates_strips_staging_root_from_absolute_path(self) -> None:
        """icloudpd emits full absolute paths; parser must strip staging root to produce relative paths."""
        staging_root = Path("C:/repo/storage/exports/icloud/chuck_icloudpd_nonrepeat_test")
        stdout = (
            "C:\\repo\\storage\\exports\\icloud\\chuck_icloudpd_nonrepeat_test\\2026\\05\\14\\IMG_5655.HEIC\n"
            "C:\\repo\\storage\\exports\\icloud\\chuck_icloudpd_nonrepeat_test\\2026\\05\\14\\IMG_5655_HEVC.MOV\n"
        )
        candidates = parse_preflight_candidates(stdout, None, staging_root=staging_root)

        self.assertEqual(len(candidates), 2)
        self.assertFalse(candidates[0].unknown_identity)
        self.assertEqual(candidates[0].normalized_source_relative_path, "2026/05/14/IMG_5655.HEIC")
        self.assertFalse(candidates[1].unknown_identity)
        self.assertEqual(candidates[1].normalized_source_relative_path, "2026/05/14/IMG_5655_HEVC.MOV")


if __name__ == "__main__":
    unittest.main()
