from __future__ import annotations

from pathlib import Path
import unittest


PACKAGING = Path(__file__).resolve().parents[1] / "packaging"


class PackagingAssetTests(unittest.TestCase):
    def test_install_is_per_user_versioned_and_quotes_uri_argument(self) -> None:
        script = (PACKAGING / "install-package.ps1").read_text(encoding="utf-8")
        self.assertIn('$version = "0.5.0"', script)
        self.assertIn("HKCU:\\Software\\Classes\\photoorganizer-helper", script)
        self.assertIn("PhotoOrganizer\\WindowsHelper", script)
        self.assertIn("'\"{0}\" \"%1\"'", script)
        self.assertNotIn("HKLM:", script)
        self.assertNotIn("credential.dpapi -Force", script)
        self.assertNotIn("helper-state.json -Force", script)

    def test_uninstall_preserves_identity_and_does_not_revoke_server(self) -> None:
        script = (PACKAGING / "uninstall-package.ps1").read_text(encoding="utf-8")
        self.assertIn("SERVER_CREDENTIAL_REVOKED=False", script)
        self.assertNotIn("credential.dpapi') -Recurse", script)
        self.assertNotIn("helper-state.json') -Recurse", script)

    def test_build_is_isolated_and_does_not_touch_retained_state(self) -> None:
        script = (PACKAGING / "build-package.ps1").read_text(encoding="utf-8")
        self.assertIn("photo-organizer-helper-build-", script)
        self.assertIn("artifact-validation", script)
        self.assertIn("Expand-Archive", script)
        self.assertIn("Start-Process", script)
        self.assertIn("-Wait", script)
        self.assertIn("$versionProcess.ExitCode -ne 0", script)
        self.assertIn("RETAINED_STATE_CHANGED=False", script)
        self.assertNotIn("credential.dpapi", script)
        self.assertNotIn("helper-state.json", script)
        self.assertNotIn("$LASTEXITCODE -eq 0 -and", script)


if __name__ == "__main__":
    unittest.main()
