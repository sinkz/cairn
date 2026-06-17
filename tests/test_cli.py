from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cairn(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "cairn", *args],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class CliSmokeTests(unittest.TestCase):
    def test_help_prints_command_list(self) -> None:
        result = run_cairn("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: cairn", result.stdout)
        self.assertIn("init", result.stdout)
        self.assertIn("search", result.stdout)
        self.assertIn("validate", result.stdout)


if __name__ == "__main__":
    unittest.main()
