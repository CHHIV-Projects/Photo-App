from __future__ import annotations

import unittest
from unittest.mock import patch

from photo_organizer_windows_helper import windows_process


class WindowsProcessTests(unittest.TestCase):
    def test_no_window_flag_is_windows_only(self) -> None:
        with patch.object(windows_process.sys, "platform", "linux"):
            self.assertEqual(windows_process.no_window_creation_flags(), 0)
        with patch.object(windows_process.sys, "platform", "win32"), patch.object(
            windows_process.subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True
        ):
            self.assertEqual(windows_process.no_window_creation_flags(), 0x08000000)


