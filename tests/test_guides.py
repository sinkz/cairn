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
    env.setdefault("APOLLOKAIRN_REGISTRY_PATH", str(ROOT / ".cairn" / f"test-registry-{os.getpid()}.json"))
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
            self.assertIn("apollokairn doctor", text)
            self.assertIn("apollokairn vault current --json", text)
            self.assertIn("apollokairn retrieve", text)
            self.assertIn("SCHEMA.md", text)
            self.assertIn("--body-file", text)
            self.assertIn("apollokairn vocab suggest", text)
            self.assertIn(
                "Run `apollokairn validate --path <vault>` and `apollokairn index --path <vault>` after every successful write",
                text,
            )

    def test_cli_setup_agent_json_reports_generated_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")

            result = run_cairn(root, "setup-agent", "codex", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["path"], "CODEX.md")

    def test_cli_setup_agent_supports_hermes_guide(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="support")

            result = run_cairn(root, "setup-agent", "hermes", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["path"], "HERMES.md")
            text = (root / "HERMES.md").read_text(encoding="utf-8")
            self.assertIn("ApolloKairn Guide for Hermes", text)
            self.assertIn("apollokairn search", text)
            self.assertIn("--json", text)

    def test_cli_setup_agent_supports_copilot_custom_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")

            result = run_cairn(root, "setup-agent", "copilot", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["path"], ".github/copilot-instructions.md")
            text = (root / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
            self.assertIn("ApolloKairn Guide for GitHub Copilot", text)
            self.assertIn("apollokairn retrieve", text)

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

    def test_cli_refresh_guides_creates_nested_configured_guide_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            config_path = root / ".cairn" / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["generated_guides"] = ["AGENTS.md", ".github/copilot-instructions.md"]
            config_path.write_text(json.dumps(config), encoding="utf-8")

            result = run_cairn(root, "refresh-guides", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(
                [item["path"] for item in payload],
                ["AGENTS.md", ".github/copilot-instructions.md"],
            )
            self.assertTrue((root / ".github" / "copilot-instructions.md").is_file())

    def test_cli_refresh_guides_rejects_paths_outside_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            init_vault(root, profile_name="personal")
            config_path = root / ".cairn" / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["generated_guides"] = ["../outside.md"]
            config_path.write_text(json.dumps(config), encoding="utf-8")

            result = run_cairn(root, "refresh-guides")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("guide path must stay inside vault", result.stderr)
            self.assertFalse((root.parent / "outside.md").exists())

    def test_public_adapter_guides_document_supported_targets(self) -> None:
        docs = [
            ROOT / "docs" / "guides" / "adapters.md",
            ROOT / "docs" / "guides" / "adapters.pt-BR.md",
        ]
        for path in docs:
            text = path.read_text(encoding="utf-8")
            for term in ("Codex", "Claude", "OpenCode", "Hermes", "GitHub Copilot"):
                self.assertIn(term, text)
            self.assertIn("setup-agent", text)
            self.assertIn("JSON", text)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        readme_pt = (ROOT / "README.pt-BR.md").read_text(encoding="utf-8")
        self.assertIn("ApolloKairn", readme)
        self.assertIn("ApolloKairn", readme_pt)
        self.assertIn("docs/guides/adapters.md", readme)
        self.assertIn("docs/guides/adapters.pt-BR.md", readme_pt)
        self.assertIn("apollokairn setup-agent", readme)
        self.assertIn("apollokairn setup-agent", readme_pt)


if __name__ == "__main__":
    unittest.main()
