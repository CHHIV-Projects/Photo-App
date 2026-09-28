"""Static safety contract for the root-owned generalized NAS installer."""

from __future__ import annotations

from pathlib import Path
import unittest


SCRIPT = Path(__file__).parents[2] / "scripts/operator/linux/register_nas_location.py"


class RegisterNasLocationInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_credentials_use_hidden_prompts_and_never_enter_arguments(self) -> None:
        self.assertIn('getpass.getpass("NAS username (hidden): ")', self.text)
        self.assertIn('getpass.getpass("NAS password (hidden): ")', self.text)
        self.assertNotIn("--username", self.text)
        self.assertNotIn("--password", self.text)
        self.assertIn('print("RAW_SECRET_PRINTED=False")', self.text)

    def test_browser_cannot_choose_host_paths_or_unit_names(self) -> None:
        self.assertIn('token = UUID(manifest["proposed_share_id"]).hex[:16]', self.text)
        self.assertIn('authority = f"/mnt/nas/photo-organizer-{token}"', self.text)
        self.assertIn('host_slot = f"/mnt/photo-organizer-sources/nas/{token}"', self.text)
        self.assertNotIn('manifest["credential_reference"]', self.text)
        self.assertNotIn('manifest["authoritative_target"]', self.text)
        self.assertNotIn('manifest["mount_unit"]', self.text)

    def test_host_commands_are_bounded_without_shell_execution(self) -> None:
        self.assertIn("timeout=timeout", self.text)
        self.assertNotIn("shell=True", self.text)
        self.assertNotIn("os.system", self.text)
        self.assertNotIn("subprocess.call", self.text)

    def test_new_credential_and_registry_modes_are_restrictive(self) -> None:
        self.assertIn("atomic_text(credential_path", self.text)
        self.assertIn("mode=0o600", self.text)
        self.assertIn("atomic_json(NAS_REGISTRY, registry, mode=0o600", self.text)
        self.assertIn("atomic_json(SOURCE_CONFIG, config, mode=0o640", self.text)

    def test_address_update_preserves_identity_and_has_rollback(self) -> None:
        self.assertIn('manifest["operation"] == "update_network_host"', self.text)
        self.assertIn("NAS_DURABLE_IDENTITY_PRESERVED=True", self.text)
        self.assertIn('shutil.copy2(rollback / "source-access.json", SOURCE_CONFIG)', self.text)
        self.assertIn('shutil.copy2(rollback / "nas-registrations.json", NAS_REGISTRY)', self.text)

    def test_namespace_must_complete_before_broker_restart_and_api_completion(self) -> None:
        self.assertIn("def require_namespace_instance_ready(instance: str)", self.text)
        self.assertEqual(self.text.count("require_namespace_instance_ready(instance)"), 2)
        first_ready = self.text.index("require_namespace_instance_ready(instance)")
        following = self.text[first_ready:]
        self.assertLess(following.index('run(["systemctl", "restart", BROKER_UNIT])'), following.index("complete_registration_with_retry(registration_id)"))


if __name__ == "__main__":
    unittest.main()
