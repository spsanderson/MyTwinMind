import unittest
from pathlib import Path

from setup_venv import (
    activation_command,
    display_python_command,
    is_windows_platform,
    venv_python_path,
)


class SetupVenvTests(unittest.TestCase):
    def test_is_windows_platform(self):
        self.assertTrue(is_windows_platform("win32"))
        self.assertFalse(is_windows_platform("linux"))

    def test_venv_python_path_windows(self):
        self.assertEqual(
            venv_python_path(Path(".venv"), "win32"),
            Path(".venv") / "Scripts" / "python.exe",
        )

    def test_venv_python_path_posix(self):
        self.assertEqual(
            venv_python_path(Path(".venv"), "linux"),
            Path(".venv") / "bin" / "python",
        )

    def test_activation_command_windows(self):
        self.assertEqual(
            activation_command(Path(".venv"), "win32"),
            r".\.venv\Scripts\Activate.ps1",
        )

    def test_activation_command_posix(self):
        self.assertEqual(
            activation_command(Path(".venv"), "linux"),
            "source .venv/bin/activate",
        )

    def test_display_python_command_windows(self):
        self.assertEqual(
            display_python_command(Path(".venv"), "win32"),
            r".\.venv\Scripts\python.exe",
        )

    def test_display_python_command_posix(self):
        self.assertEqual(
            display_python_command(Path(".venv"), "linux"),
            ".venv/bin/python",
        )


if __name__ == "__main__":
    unittest.main()
