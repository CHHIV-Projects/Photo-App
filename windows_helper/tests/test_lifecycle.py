from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from photo_organizer_windows_helper.cli import run
from photo_organizer_windows_helper.credential_store import StoredCredential, default_state_directory
from photo_organizer_windows_helper.lifecycle import (
    START_URI,
    WINDOWS_NORMALIZED_START_URI,
    IdleDeadline,
    SingleInstance,
    mutex_name,
    parse_start_uri,
)
from photo_organizer_windows_helper.logging_config import configure_file_logging


class _Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


class _MutexApi:
    def __init__(self, owned: bool) -> None:
        self.owned = owned
        self.closed: list[object] = []

    def create(self, name: str) -> tuple[object, bool]:
        self.name = name
        return object(), self.owned

    def close(self, handle: object) -> None:
        self.closed.append(handle)


class LifecycleTests(unittest.TestCase):
    def test_uri_parser_accepts_only_exact_windows_start_forms_without_injection_surface(self) -> None:
        self.assertEqual(parse_start_uri(START_URI), "start")
        self.assertEqual(parse_start_uri(WINDOWS_NORMALIZED_START_URI), "start")
        rejected = [
            "photoorganizer-helper://stop",
            "photoorganizer-helper://stop/",
            "photoorganizer-helper://start//",
            "photoorganizer-helper://start/extra",
            "photoorganizer-helper://start?command=calc.exe",
            "photoorganizer-helper://start/?command=calc.exe",
            "photoorganizer-helper://start#fragment",
            "photoorganizer-helper://start/#fragment",
            "photoorganizer-helper://start%20--host=attacker",
            'photoorganizer-helper://start";calc.exe',
            "PHOTOORGANIZER-HELPER://start",
        ]
        for value in rejected:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_start_uri(value)

    def test_mutex_reuses_existing_owned_instance_and_never_terminates_processes(self) -> None:
        api = _MutexApi(owned=False)
        instance = SingleInstance(mutex_name("safe-node-id"), api=api)
        self.assertFalse(instance.acquire())
        self.assertEqual(len(api.closed), 1)
        self.assertNotIn("safe-node-id", api.name)

    def test_mutex_releases_only_its_own_handle(self) -> None:
        api = _MutexApi(owned=True)
        instance = SingleInstance("safe-name", api=api)
        self.assertTrue(instance.acquire())
        instance.close()
        self.assertEqual(len(api.closed), 1)

    def test_idle_exit_is_bounded_and_active_work_prevents_exit(self) -> None:
        clock = _Clock()
        idle = IdleDeadline(600, clock=clock)
        clock.value = 601
        idle.set_busy(True)
        clock.value = 5000
        self.assertFalse(idle.should_exit())
        idle.set_busy(False)
        self.assertFalse(idle.should_exit())
        clock.value = 5601
        self.assertTrue(idle.should_exit())

    def test_rotating_log_redacts_protected_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            logger = configure_file_logging(Path(temporary))
            logger.error("credential=raw token:also-raw password=hidden pairing_code=secret")
            for handler in logger.handlers:
                handler.flush()
            content = (Path(temporary) / "logs" / "helper.log").read_text(encoding="utf-8")
            self.assertNotIn("raw", content)
            self.assertNotIn("hidden", content)
            self.assertNotIn("secret", content)
            self.assertIn("[REDACTED]", content)
            handler = logger.handlers[0]
            self.assertEqual(handler.maxBytes, 512 * 1024)
            self.assertEqual(handler.backupCount, 3)

    def test_duplicate_packaged_start_does_not_open_tunnel(self) -> None:
        credential = StoredCredential(
            access_node_id="11111111-1111-1111-1111-111111111111",
            credential_id="public",
            credential_version=1,
            token="protected",
        )
        store = MagicMock()
        store.load.return_value = credential
        store.state_directory = Path("C:/state")
        instance = MagicMock()
        instance.__enter__.return_value = instance
        instance.acquire.return_value = False
        with patch("photo_organizer_windows_helper.cli.DpapiCredentialStore", return_value=store), patch(
            "photo_organizer_windows_helper.cli.configure_file_logging", return_value=MagicMock()
        ), patch("photo_organizer_windows_helper.cli.SingleInstance", return_value=instance), patch(
            "photo_organizer_windows_helper.cli.TunnelManager"
        ) as tunnel:
            self.assertEqual(run([START_URI]), 0)
        tunnel.assert_not_called()

    def test_retained_state_path_is_outside_versioned_bin(self) -> None:
        with patch.dict("os.environ", {"LOCALAPPDATA": "C:/Users/test/AppData/Local"}, clear=False):
            root = default_state_directory()
        self.assertEqual(root.name, "WindowsHelper")
        self.assertNotIn("bin", root.parts)


if __name__ == "__main__":
    unittest.main()
