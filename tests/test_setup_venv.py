import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from setup_venv import (
    activation_command,
    display_python_command,
    is_windows_platform,
    should_create_virtualenv,
    same_path,
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

    def test_should_create_virtualenv_when_python_missing(self):
        with TemporaryDirectory() as tmp:
            missing_python = Path(tmp) / ".venv" / "Scripts" / "python.exe"
            self.assertTrue(
                should_create_virtualenv(
                    Path(".venv"), missing_python, recreate=False
                )
            )

    def test_should_create_virtualenv_when_recreate_requested(self):
        self.assertTrue(
            should_create_virtualenv(Path(".venv"), Path(__file__), recreate=True)
        )

    def test_should_reuse_existing_virtualenv_by_default(self):
        self.assertFalse(
            should_create_virtualenv(Path(".venv"), Path(__file__), recreate=False)
        )

    def test_same_path_accepts_equivalent_paths(self):
        self.assertTrue(same_path(Path("."), Path.cwd()))


if __name__ == "__main__":
    unittest.main()
