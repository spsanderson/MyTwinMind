import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class GitignorePolicyTests(unittest.TestCase):
    def assert_git_ignores(self, path: str):
        result = subprocess.run(
            ["git", "check-ignore", "--verbose", "--", path],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"Expected git to ignore {path!r}. stderr: {result.stderr}",
        )

    def test_private_twinmind_state_and_default_exports_are_ignored(self):
        self.assert_git_ignores(".auth/twinmind_state.json")
        self.assert_git_ignores("memories/example.md")
        self.assert_git_ignores("twinmind_memories.db")


if __name__ == "__main__":
    unittest.main()
