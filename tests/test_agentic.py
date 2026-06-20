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

from cairn.agentic import ASSET_FILES, README_MD


def run_cairn(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env.setdefault("APOLLOKAIRN_REGISTRY_PATH", str(ROOT / ".cairn" / f"test-registry-{os.getpid()}.json"))
    return subprocess.run(
        [sys.executable, "-m", "cairn", *args],
        cwd=cwd or ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class AgenticTests(unittest.TestCase):
    def test_versioned_skill_is_spec_shaped_and_succinct(self) -> None:
        skill_dir = ROOT / "agentic" / "skills" / "apollokairn-vault"
        skill_path = skill_dir / "SKILL.md"

        text = skill_path.read_text(encoding="utf-8")

        self.assertTrue(skill_path.is_file())
        self.assertLess(len(text), 3200)
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("name: apollokairn-vault", text)
        self.assertIn("description:", text)
        self.assertEqual(skill_dir.name, "apollokairn-vault")
        self.assertTrue((skill_dir / "references" / "commands.md").is_file())
        self.assertTrue((skill_dir / "references" / "workflows.md").is_file())
        self.assertEqual((ROOT / "agentic" / "README.md").read_text(encoding="utf-8"), README_MD)
        for relative, embedded in ASSET_FILES.items():
            self.assertEqual((skill_dir / relative).read_text(encoding="utf-8"), embedded)

    def test_install_codex_user_copy_to_custom_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target_dir = Path(tmp) / "codex-skills"

            result = run_cairn("agent", "install", "codex", "--target-dir", str(target_dir), "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            skill_dir = target_dir / "apollokairn-vault"
            self.assertEqual(payload["agent"], "codex")
            self.assertEqual(payload["mode"], "copy")
            self.assertEqual(Path(payload["path"]), skill_dir)
            self.assertTrue(payload["changed"])
            self.assertTrue((skill_dir / "SKILL.md").is_file())
            self.assertTrue((skill_dir / "references" / "commands.md").is_file())

            second = run_cairn("agent", "install", "codex", "--target-dir", str(target_dir), "--json")
            self.assertEqual(second.returncode, 0, second.stderr)
            second_payload = json.loads(second.stdout)
            self.assertFalse(second_payload["changed"])
            self.assertFalse(second_payload["would_change"])
            self.assertEqual(second_payload["message"], "already installed")

    def test_install_hermes_user_copy_to_custom_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target_dir = Path(tmp) / "hermes-skills"

            result = run_cairn("agent", "install", "hermes", "--target-dir", str(target_dir), "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            skill_dir = target_dir / "apollokairn-vault"
            self.assertEqual(payload["agent"], "hermes")
            self.assertEqual(payload["scope"], "user")
            self.assertTrue((skill_dir / "SKILL.md").is_file())

    def test_install_codex_repo_scope_uses_repo_agents_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()

            result = run_cairn("agent", "install", "codex", "--scope", "repo", "--path", str(repo), "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            skill_dir = repo / ".agents" / "skills" / "apollokairn-vault"
            self.assertEqual(Path(payload["skills_dir"]), repo / ".agents" / "skills")
            self.assertTrue((skill_dir / "SKILL.md").is_file())

    def test_agent_doctor_reports_missing_and_installed_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target_dir = Path(tmp) / "skills"

            missing = run_cairn("agent", "doctor", "codex", "--target-dir", str(target_dir), "--json")
            self.assertEqual(missing.returncode, 1)
            missing_payload = json.loads(missing.stdout)
            self.assertFalse(missing_payload["ok"])
            self.assertFalse(missing_payload["checks"][0]["installed"])

            installed = run_cairn("agent", "install", "codex", "--target-dir", str(target_dir), "--json")
            self.assertEqual(installed.returncode, 0, installed.stderr)
            doctor = run_cairn("agent", "doctor", "codex", "--target-dir", str(target_dir), "--json")

            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            payload = json.loads(doctor.stdout)
            self.assertTrue(payload["ok"])
            self.assertTrue(payload["checks"][0]["installed"])

    def test_agent_install_symlink_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target_dir = Path(tmp) / "skills"

            result = run_cairn(
                "agent",
                "install",
                "codex",
                "--target-dir",
                str(target_dir),
                "--mode",
                "symlink",
                "--dry-run",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["mode"], "symlink")
            self.assertFalse(payload["changed"])
            self.assertTrue(payload["would_change"])
            self.assertFalse((target_dir / "apollokairn-vault").exists())

    def test_install_claude_code_user_copy_to_custom_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target_dir = Path(tmp) / "claude-skills"

            result = run_cairn("agent", "install", "claude-code", "--target-dir", str(target_dir), "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            skill_dir = target_dir / "apollokairn-vault"
            self.assertEqual(payload["agent"], "claude-code")
            self.assertEqual(payload["mode"], "copy")
            self.assertTrue(payload["changed"])
            self.assertTrue((skill_dir / "SKILL.md").is_file())
            self.assertTrue((skill_dir / "references" / "commands.md").is_file())

    def test_install_claude_code_repo_scope_uses_repo_claude_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()

            result = run_cairn(
                "agent", "install", "claude-code", "--scope", "repo", "--path", str(repo), "--json"
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            skill_dir = repo / ".claude" / "skills" / "apollokairn-vault"
            self.assertEqual(Path(payload["skills_dir"]), repo / ".claude" / "skills")
            self.assertTrue((skill_dir / "SKILL.md").is_file())

    def test_default_skills_dir_claude_code_user_scope(self) -> None:
        from cairn.agentic import default_skills_dir

        self.assertEqual(default_skills_dir("claude-code", "user"), Path.home() / ".claude" / "skills")


if __name__ == "__main__":
    unittest.main()
