from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cairn.cli import main


def run_cairn_module(
    *args: str,
    cwd: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env.setdefault("APOLLOKAIRN_REGISTRY_PATH", str(ROOT / ".cairn" / f"test-registry-{os.getpid()}.json"))
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-m", "cairn", *args],
        cwd=cwd or ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class CliSmokeTests(unittest.TestCase):
    def isolated_registry(self, temp: Path) -> dict[str, str]:
        return {"APOLLOKAIRN_REGISTRY_PATH": str(temp / "registry.json")}

    def init_temp_vault(self, temp: Path, name: str = "vault") -> Path:
        vault = temp / name
        result = run_cairn_module(
            "init",
            "--path",
            str(vault),
            "--profile",
            "engineering",
            extra_env=self.isolated_registry(temp),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return vault

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

    def test_vault_commands_manage_named_active_vaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            env = self.isolated_registry(temp)
            vault = self.init_temp_vault(temp, "work")

            add = run_cairn_module("vault", "add", str(vault), "--name", "work", "--set-active", "--json", extra_env=env)
            self.assertEqual(add.returncode, 0, add.stderr)
            self.assertEqual(json.loads(add.stdout)["name"], "work")

            listing = run_cairn_module("vault", "list", "--json", extra_env=env)
            self.assertEqual(listing.returncode, 0, listing.stderr)
            payload = json.loads(listing.stdout)
            self.assertEqual(payload["active"], "work")
            self.assertEqual(payload["vaults"][0]["name"], "work")
            self.assertTrue(payload["vaults"][0]["is_vault"])

            current = run_cairn_module("vault", "current", "--json", extra_env=env)
            self.assertEqual(current.returncode, 0, current.stderr)
            self.assertEqual(json.loads(current.stdout)["name"], "work")

            show = run_cairn_module("vault", "show", "work", "--json", extra_env=env)
            self.assertEqual(show.returncode, 0, show.stderr)
            self.assertEqual(json.loads(show.stdout)["name"], "work")

            doctor = run_cairn_module("vault", "doctor", "--json", extra_env=env)
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            self.assertTrue(json.loads(doctor.stdout)["ok"])

            remove = run_cairn_module("vault", "remove", "work", "--json", extra_env=env)
            self.assertEqual(remove.returncode, 0, remove.stderr)
            self.assertEqual(json.loads(remove.stdout)["name"], "work")

            empty_current = run_cairn_module("vault", "current", "--json", extra_env=env)
            self.assertEqual(empty_current.returncode, 1)
            self.assertIn("no active vault", empty_current.stderr)

    def test_registered_vault_can_be_used_from_another_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            env = self.isolated_registry(temp)
            vault = self.init_temp_vault(temp, "knowledge")
            add_note = run_cairn_module(
                "capture",
                "--path",
                str(vault),
                "--title",
                "Deploy 403 token rotation",
                "--description",
                "Fixes deploy failures after rotating CI tokens.",
                "--type",
                "Runbook",
                "--tag",
                "deploy",
                "--body",
                "Update the CI token secret and rerun the failed deploy.",
                extra_env=env,
            )
            self.assertEqual(add_note.returncode, 0, add_note.stderr)
            indexed = run_cairn_module("index", "--path", str(vault), "--rebuild", extra_env=env)
            self.assertEqual(indexed.returncode, 0, indexed.stderr)
            registered = run_cairn_module("vault", "add", str(vault), "--name", "work", "--json", extra_env=env)
            self.assertEqual(registered.returncode, 0, registered.stderr)

            outside = temp / "outside"
            outside.mkdir()
            found = run_cairn_module("search", "deploy 403", "--vault", "work", "--json", cwd=outside, extra_env=env)

        self.assertEqual(found.returncode, 0, found.stderr)
        self.assertEqual(json.loads(found.stdout)[0]["title"], "Deploy 403 token rotation")

    def test_active_vault_is_used_when_path_and_vault_are_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            env = self.isolated_registry(temp)
            vault = self.init_temp_vault(temp, "active")
            result = run_cairn_module(
                "capture",
                "--path",
                str(vault),
                "--title",
                "Webhook 400 schema drift",
                "--description",
                "Fixes webhook failures after schema changes.",
                "--type",
                "Runbook",
                "--tag",
                "bug",
                "--body",
                "Update the webhook parser to accept the provider schema.",
                extra_env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            indexed = run_cairn_module("index", "--path", str(vault), "--rebuild", extra_env=env)
            self.assertEqual(indexed.returncode, 0, indexed.stderr)
            active = run_cairn_module("vault", "add", str(vault), "--name", "active", "--set-active", extra_env=env)
            self.assertEqual(active.returncode, 0, active.stderr)

            outside = temp / "outside"
            outside.mkdir()
            found = run_cairn_module("search", "webhook schema", "--json", cwd=outside, extra_env=env)

        self.assertEqual(found.returncode, 0, found.stderr)
        self.assertEqual(json.loads(found.stdout)[0]["title"], "Webhook 400 schema drift")


if __name__ == "__main__":
    unittest.main()
