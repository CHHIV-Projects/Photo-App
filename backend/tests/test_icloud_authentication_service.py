from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.ingestion_source import IngestionSource
from app.services import icloud_authentication_helper as helper
from app.services import icloud_authentication_service as service


class _FakeProcess:
    def __init__(self) -> None:
        self.alive = True

    def poll(self) -> int | None:
        return None if self.alive else 0

    def terminate(self) -> None:
        self.alive = False

    def kill(self) -> None:
        self.alive = False

    def wait(self, timeout: int | None = None) -> int:
        self.alive = False
        return 0


class PyiCloudAPIResponseException(Exception):
    def __init__(self, reason: str, code: str) -> None:
        super().__init__("provider response withheld")
        self.reason = reason
        self.code = code


class PyiCloudFailedLoginException(Exception):
    pass


class IcloudAuthenticationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        service._sessions.clear()
        service._source_sessions.clear()
        self.db = MagicMock()
        self.source = IngestionSource(
            id=13,
            source_label="Family iCloud",
            source_label_normalized="family_icloud",
            source_type="cloud_export",
            source_root_path="/app/storage/exports/icloud/family_icloud",
            source_root_path_normalized="/app/storage/exports/icloud/family_icloud",
            profile_status="active",
            cloud_provider="icloud",
            acquisition_method="icloudpd",
            managed_staging_path="/app/storage/exports/icloud/family_icloud",
            account_username="family@example.com",
        )
        self.db.get.return_value = self.source

    def tearDown(self) -> None:
        service._sessions.clear()
        service._source_sessions.clear()

    def test_password_then_mfa_succeeds_without_secret_in_snapshot(self) -> None:
        process = _FakeProcess()
        started = service.start_icloud_authentication(self.db, source_profile_id=13)
        with patch.object(service, "_account_auth_directory"), patch.object(
            service,
            "_start_provider_process",
            return_value=process,
        ), patch.object(
            service,
            "_send_provider_request",
            side_effect=[
                {"state": "mfa_required", "message": "Enter a code.", "retryable": True},
                {"state": "authenticated", "message": "Signed in.", "retryable": False},
            ],
        ):
            prompted = service.submit_icloud_password(
                self.db,
                session_id=started.session_id,
                source_profile_id=13,
                password="not-recorded-secret",
            )
            completed = service.submit_icloud_mfa(
                self.db,
                session_id=started.session_id,
                source_profile_id=13,
                code="123456",
            )
        self.assertEqual(prompted.state, "mfa_required")
        self.assertNotIn("not-recorded-secret", repr(prompted))
        self.assertEqual(completed.state, "authenticated")
        self.assertNotIn("123456", repr(completed))
        self.assertNotIn(started.session_id, service._sessions)

    def test_invalid_mfa_is_retryable(self) -> None:
        process = _FakeProcess()
        started = service.start_icloud_authentication(self.db, source_profile_id=13)
        with patch.object(service, "_account_auth_directory"), patch.object(
            service,
            "_start_provider_process",
            return_value=process,
        ), patch.object(
            service,
            "_send_provider_request",
            side_effect=[
                {"state": "mfa_required", "message": "Enter a code.", "retryable": True},
                {"state": "mfa_required", "message": "Try again.", "retryable": True},
            ],
        ):
            service.submit_icloud_password(
                self.db,
                session_id=started.session_id,
                source_profile_id=13,
                password="secret",
            )
            result = service.submit_icloud_mfa(
                self.db,
                session_id=started.session_id,
                source_profile_id=13,
                code="000000",
            )
        self.assertEqual(result.state, "mfa_required")
        self.assertTrue(result.retryable)

    def test_duplicate_start_reuses_one_session_and_cross_source_fails(self) -> None:
        first = service.start_icloud_authentication(self.db, source_profile_id=13)
        second = service.start_icloud_authentication(self.db, source_profile_id=13)
        self.assertEqual(first.session_id, second.session_id)
        with self.assertRaises(service.IcloudAuthenticationError):
            service.cancel_icloud_authentication(session_id=first.session_id, source_profile_id=99)

    def test_cancel_invalidates_session_without_source_mutation(self) -> None:
        started = service.start_icloud_authentication(self.db, source_profile_id=13)
        process = _FakeProcess()
        service._sessions[started.session_id].provider = process
        before = self.source.source_root_path
        cancelled = service.cancel_icloud_authentication(
            session_id=started.session_id,
            source_profile_id=13,
        )
        self.assertEqual(cancelled.state, "cancelled")
        self.assertEqual(self.source.source_root_path, before)
        self.assertFalse(process.alive)

    def test_provider_command_is_fixed_and_contains_no_secret(self) -> None:
        fake_process = _FakeProcess()
        with patch.object(
            service,
            "settings",
            SimpleNamespace(
                icloud_provider_python_path=sys.executable,
                icloud_auth_state_path="/tmp/photo-organizer-icloud-auth-test",
            ),
        ), patch.object(service.subprocess, "Popen", return_value=fake_process) as popen:
            result = service._start_provider_process()
        self.assertIs(result, fake_process)
        command = popen.call_args.args[0]
        self.assertEqual(command, [sys.executable, str(service._HELPER_SCRIPT)])
        self.assertNotIn("password", " ".join(command).lower())
        provider_env = popen.call_args.kwargs["env"]
        self.assertEqual(
            provider_env["ICLOUD_AUTH_STATE_PATH"],
            "/tmp/photo-organizer-icloud-auth-test",
        )
        self.assertNotIn("DATABASE_URL", provider_env)
        self.assertNotIn("POSTGRES_PASSWORD", provider_env)

    def test_expired_session_cannot_be_reused(self) -> None:
        started = service.start_icloud_authentication(self.db, source_profile_id=13)
        service._sessions[started.session_id].expires_at = service._utcnow()
        with self.assertRaises(service.IcloudAuthenticationError) as raised:
            service.cancel_icloud_authentication(
                session_id=started.session_id,
                source_profile_id=13,
            )
        self.assertEqual(raised.exception.code, "expired")

    def test_auth_directory_is_hashed_private_and_contains_no_account_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            service,
            "settings",
            SimpleNamespace(icloud_auth_state_path=temp_dir),
        ):
            path = service._account_auth_directory("family@example.com")
            self.assertNotIn("family", path.name)
            self.assertEqual(path.stat().st_mode & 0o777, 0o700)

    def test_locked_account_error_is_classified_without_provider_text(self) -> None:
        provider_error = PyiCloudAPIResponseException(
            '{"serviceErrors":[{"code":"-20209","message":"sensitive provider text"}]}',
            "403",
        )
        failed_login = PyiCloudFailedLoginException("generic", provider_error)
        failed_login.__cause__ = provider_error

        state, message, retryable = helper._safe_exception_state(failed_login)

        self.assertEqual(state, "authentication_failed")
        self.assertIn("account is locked", message)
        self.assertNotIn("sensitive provider text", message)
        self.assertFalse(retryable)

    def test_app_specific_password_error_is_classified_safely(self) -> None:
        provider_error = PyiCloudAPIResponseException(
            '{"service_errors":[{"code":-20283,"message":"sensitive provider text"}]}',
            "401",
        )
        failed_login = PyiCloudFailedLoginException("generic", provider_error)
        failed_login.__cause__ = provider_error

        state, message, retryable = helper._safe_exception_state(failed_login)

        self.assertEqual(state, "authentication_failed")
        self.assertIn("regular Apple Account password", message)
        self.assertNotIn("sensitive provider text", message)
        self.assertFalse(retryable)

    def test_modern_mfa_wins_when_provider_sets_both_auth_predicates(self) -> None:
        provider = SimpleNamespace(requires_2fa=True, requires_2sa=True)

        self.assertEqual(helper._authentication_requirement(provider), "modern_mfa")

    def test_legacy_verification_requires_absent_modern_mfa(self) -> None:
        provider = SimpleNamespace(requires_2fa=False, requires_2sa=True)

        self.assertEqual(helper._authentication_requirement(provider), "legacy_verification")


if __name__ == "__main__":
    unittest.main()
