from __future__ import annotations

import io
import os
import subprocess
import sys
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cairn.cli import main


def run_cairn_module(*args: str) -> subprocess.CompletedProcess[str]:
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
    def test_help_prints_public_command_name(self) -> None:
        result = run_cairn_module("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: apollokairn", result.stdout)
        self.assertIn("init", result.stdout)
        self.assertIn("search", result.stdout)
        self.assertIn("validate", result.stdout)

    def test_version_prints_public_command_name_and_package_version(self) -> None:
        version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]

        result = run_cairn_module("--version")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), f"apollokairn {version}")
        self.assertEqual(result.stderr, "")

    def test_pyproject_registers_public_aliases_and_legacy_alias(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(project["project"]["name"], "apollokairn-cli")
        self.assertEqual(project["project"]["scripts"]["apollokairn"], "cairn.cli:main")
        self.assertEqual(project["project"]["scripts"]["ak"], "cairn.cli:main")
        self.assertEqual(project["project"]["scripts"]["cairn"], "cairn.cli:main")

    def test_legacy_invocation_emits_deprecation_warning(self) -> None:
        out = io.StringIO()
        err = io.StringIO()

        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = main(["--help"], invoked_as="cairn")
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1

        self.assertEqual(code, 0)
        self.assertIn("usage: apollokairn", out.getvalue())
        self.assertIn("WARNING: `cairn` is deprecated; use `apollokairn` instead.", err.getvalue())

    def test_public_invocation_does_not_emit_deprecation_warning(self) -> None:
        out = io.StringIO()
        err = io.StringIO()

        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = main(["--help"], invoked_as="apollokairn")
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1

        self.assertEqual(code, 0)
        self.assertIn("usage: apollokairn", out.getvalue())
        self.assertEqual(err.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
