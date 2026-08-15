from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from photo_organizer_windows_helper.ssh_policy import verify_ssh_configuration
from photo_organizer_windows_helper.tunnel import tunnel_arguments


SAFE_CONFIG = """\
stricthostkeychecking true
exitonforwardfailure yes
gatewayports no
permitlocalcommand no
sessiontype none
hostname example.invalid
"""


class SshPolicyTests(unittest.TestCase):
    def test_effective_configuration_without_extra_forwards_is_accepted(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout=SAFE_CONFIG, stderr="")
        with patch(
            "photo_organizer_windows_helper.ssh_policy.subprocess.run", return_value=completed
        ) as run:
            self.assertTrue(verify_ssh_configuration("ssh.exe", tunnel_arguments()))
        arguments, keywords = run.call_args
        self.assertIn("-G", arguments[0])
        self.assertNotIn("-L", arguments[0])
        self.assertFalse(keywords["shell"])

    def test_config_injected_forward_or_weakened_host_key_policy_is_rejected(self) -> None:
        for extra in (
            "localforward 127.0.0.1:9 127.0.0.1:9\n",
            "remoteforward 9 127.0.0.1:9\n",
            "dynamicforward 1080\n",
        ):
            completed = subprocess.CompletedProcess([], 0, stdout=SAFE_CONFIG + extra, stderr="")
            with patch(
                "photo_organizer_windows_helper.ssh_policy.subprocess.run", return_value=completed
            ):
                self.assertFalse(verify_ssh_configuration("ssh.exe", tunnel_arguments()))

        weakened = SAFE_CONFIG.replace("stricthostkeychecking true", "stricthostkeychecking ask")
        completed = subprocess.CompletedProcess([], 0, stdout=weakened, stderr="")
        with patch(
            "photo_organizer_windows_helper.ssh_policy.subprocess.run", return_value=completed
        ):
            self.assertFalse(verify_ssh_configuration("ssh.exe", tunnel_arguments()))


if __name__ == "__main__":
    unittest.main()
