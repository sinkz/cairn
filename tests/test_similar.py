from __future__ import annotations

import os
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cairn.vault import init_vault
from cairn.similar import similar_kind


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


class SimilarTests(unittest.TestCase):
    def test_cli_similar_returns_existing_note_before_capture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            (root / "knowledge" / "deploy-403.md").write_text(
                "---\n"
                "type: Runbook\n"
                "title: Deploy 403 after token rotation\n"
                "description: Fix stale CI token after workspace access changes.\n"
                "tags: [bug, deploy]\n"
                "timestamp: 2026-06-17T10:00:00Z\n"
                "aliases: [deploy forbidden]\n"
                "systems: [ci]\n"
                "signals: [http 403]\n"
                "---\n\n"
                "# Context\n\nDeploy fails with HTTP 403 after rotating workspace token.\n",
                encoding="utf-8",
            )
            run_cairn(root, "index", "--rebuild")

            result = run_cairn(root, "similar", "deploy forbidden token", "--limit", "3")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("knowledge/deploy-403.md", result.stdout)
            self.assertIn("duplicate_candidate", result.stdout)
            self.assertIn("similarity=", result.stdout)

    def test_similar_kind_labels_strong_and_moderate_matches(self) -> None:
        self.assertEqual(similar_kind(0.9), "duplicate_candidate")
        self.assertEqual(similar_kind(0.65), "related")

    def test_cli_similar_json_includes_similarity_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            (root / "knowledge" / "deploy-403.md").write_text(
                "---\n"
                "type: Runbook\n"
                "title: Deploy 403 token\n"
                "description: Fix deploy forbidden token errors.\n"
                "tags: [bug, deploy]\n"
                "timestamp: 2026-06-17T10:00:00Z\n"
                "aliases: [deploy forbidden]\n"
                "systems: [ci]\n"
                "signals: [http 403]\n"
                "---\n\n"
                "# Context\n\nDeploy forbidden token 403.\n",
                encoding="utf-8",
            )
            run_cairn(root, "index", "--rebuild")

            result = run_cairn(root, "similar", "deploy forbidden token", "--limit", "1", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload[0]["path"], "knowledge/deploy-403.md")
            self.assertGreaterEqual(payload[0]["similarity"], 0.2)
            self.assertEqual(payload[0]["kind"], "duplicate_candidate")

    def test_cli_similar_finds_near_duplicate_with_extra_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            (root / "knowledge" / "deploy-token-rotation.md").write_text(
                "---\n"
                "type: Runbook\n"
                "title: Deploy token rotation\n"
                "description: Update the CI secret after rotating workspace access.\n"
                "tags: [bug, deploy]\n"
                "timestamp: 2026-06-17T10:00:00Z\n"
                "aliases: [deploy forbidden]\n"
                "systems: [ci]\n"
                "signals: [http 403, token rotation]\n"
                "---\n\n"
                "# Context\n\n"
                "Deployment failed after the workspace token rotation.\n\n"
                "# Resolution\n\n"
                "Update the CI secret and rerun the failed deployment job.\n",
                encoding="utf-8",
            )
            run_cairn(root, "index", "--rebuild")
            query = (
                "After rotating workspace access, deployment fails until the CI "
                "secret is updated and the failed job is rerun. kubernetes staging"
            )

            result = run_cairn(root, "similar", query, "--limit", "3", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload[0]["path"], "knowledge/deploy-token-rotation.md")
            self.assertGreaterEqual(payload[0]["similarity"], 0.55)
            self.assertIn(payload[0]["kind"], {"duplicate_candidate", "related"})


if __name__ == "__main__":
    unittest.main()
