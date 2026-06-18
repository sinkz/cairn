from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cairn.vault import init_vault


def run_cairn(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "cairn", *args],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def add_note(root: Path) -> None:
    result = run_cairn(
        root,
        "add",
        "--title",
        "Deploy 403",
        "--type",
        "Runbook",
        "--description",
        "Fix deploy authorization failures.",
        "--tag",
        "bug",
        "--tag",
        "deploy",
        "--body",
        "Rotate the CI token.",
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)


class OpsTests(unittest.TestCase):
    def test_cli_stats_json_counts_documents_types_and_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            add_note(root)

            result = run_cairn(root, "stats", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["documents"], 1)
            self.assertEqual(payload["types"]["Runbook"], 1)
            self.assertEqual(payload["tags"]["bug"], 1)
            self.assertGreater(payload["estimated_tokens"], 0)

    def test_cli_export_and_import_roundtrip_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            target = base / "target"
            archive = base / "vault.zip"
            init_vault(source, profile_name="engineering")
            add_note(source)
            run_cairn(source, "index", "--rebuild")

            exported = run_cairn(source, "export", "--output", str(archive))
            imported = run_cairn(source, "import", str(archive), "--path", str(target))

            self.assertEqual(exported.returncode, 0, exported.stderr)
            self.assertEqual(imported.returncode, 0, imported.stderr)
            self.assertTrue((target / "knowledge" / "deploy-403.md").is_file())
            self.assertFalse((target / ".cairn" / "index.db").exists())

    def test_cli_export_and_import_json_report_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            target = base / "target"
            archive = base / "vault.zip"
            init_vault(source, profile_name="engineering")
            add_note(source)

            exported = run_cairn(source, "export", "--output", str(archive), "--json")
            imported = run_cairn(source, "import", str(archive), "--path", str(target), "--json")

            self.assertEqual(exported.returncode, 0, exported.stderr)
            self.assertEqual(imported.returncode, 0, imported.stderr)
            self.assertEqual(Path(json.loads(exported.stdout)["output"]), archive)
            self.assertEqual(Path(json.loads(imported.stdout)["root"]), target)

    def test_cli_export_inside_vault_does_not_include_archive_itself(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            add_note(root)
            archive = root / "vault.zip"

            result = run_cairn(root, "export", "--output", str(archive))

            self.assertEqual(result.returncode, 0, result.stderr)
            with ZipFile(archive) as zf:
                self.assertNotIn("vault.zip", zf.namelist())

    def test_cli_export_blocks_secret_like_values_without_echoing_them(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            secret_value = "AKIAIOSFODNN7EXAMPLE"
            (root / "knowledge" / "secret.md").write_text(
                "---\n"
                "type: Runbook\n"
                "title: Secret export\n"
                "description: Should block export.\n"
                "tags: [bug]\n"
                "timestamp: 2026-06-17T10:00:00Z\n"
                "---\n\n"
                "# Context\n\n"
                f"Do not export AWS access key {secret_value}.\n",
                encoding="utf-8",
            )
            archive = Path(tmp) / "vault.zip"

            result = run_cairn(root, "export", "--output", str(archive))

            self.assertEqual(result.returncode, 1)
            self.assertFalse(archive.exists())
            self.assertIn("potential secret", result.stderr)
            self.assertIn("knowledge/secret.md", result.stderr)
            self.assertNotIn(secret_value, result.stderr)

    def test_cli_doctor_reports_invalid_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            (root / ".cairn" / "config.json").write_text('{"exclude": "inbox"}', encoding="utf-8")

            result = run_cairn(root, "doctor")

            self.assertEqual(result.returncode, 1)
            self.assertIn("ERROR config", result.stdout)


if __name__ == "__main__":
    unittest.main()
