from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


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


class GuidesTests(unittest.TestCase):
    def test_cli_setup_agent_creates_codex_guide(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")

            result = run_cairn(root, "setup-agent", "codex")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / "CODEX.md").is_file())
            text = (root / "CODEX.md").read_text(encoding="utf-8")
            self.assertIn("cairn doctor", text)
            self.assertIn("cairn retrieve", text)
            self.assertIn("SCHEMA.md", text)
            self.assertIn("--body-file", text)
            self.assertIn("cairn vocab suggest", text)
            self.assertIn("Run `cairn validate --path <vault>` and `cairn index --path <vault>` after every successful write", text)

    def test_cli_setup_agent_json_reports_generated_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")

            result = run_cairn(root, "setup-agent", "codex", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["path"], "CODEX.md")

    def test_cli_refresh_guides_uses_configured_generated_guides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            config_path = root / ".cairn" / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["generated_guides"] = ["AGENTS.md", "CLAUDE.md", "OPENCODE.md"]
            config_path.write_text(json.dumps(config), encoding="utf-8")

            result = run_cairn(root, "refresh-guides")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / "AGENTS.md").is_file())
            self.assertTrue((root / "CLAUDE.md").is_file())
            self.assertTrue((root / "OPENCODE.md").is_file())
            self.assertIn("updated CLAUDE.md", result.stdout)

    def test_cli_refresh_guides_json_reports_all_generated_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            config_path = root / ".cairn" / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["generated_guides"] = ["AGENTS.md", "CLAUDE.md"]
            config_path.write_text(json.dumps(config), encoding="utf-8")

            result = run_cairn(root, "refresh-guides", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual([item["path"] for item in payload], ["AGENTS.md", "CLAUDE.md"])


if __name__ == "__main__":
    unittest.main()
