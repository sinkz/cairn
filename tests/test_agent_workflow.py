from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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


class AgentWorkflowTests(unittest.TestCase):
    def test_agent_can_capture_search_retrieve_similar_and_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            init = run_cairn(root.parent, "init", "--path", str(root), "--profile", "engineering")
            capture = run_cairn(
                root,
                "capture",
                "--title",
                "Deploy 403 token rotation",
                "--description",
                "Fix deploy failure after CI token rotation.",
                "--type",
                "Runbook",
                "--tag",
                "bug",
                "--tag",
                "deploy",
                "--system",
                "ci",
                "--alias",
                "deploy forbidden",
                "--signal",
                "HTTP 403",
                "--body",
                "# Context\n\nDeploy fails with HTTP 403.\n\n# Resolution\n\nRotate the CI token.",
            )
            index = run_cairn(root, "index", "--rebuild")
            search = run_cairn(root, "search", "deploy 403 token", "--json")
            retrieve = run_cairn(root, "retrieve", "rotate ci token", "--mode", "passages", "--budget", "300")
            similar = run_cairn(root, "similar", "deploy forbidden token rotation", "--json")
            update = run_cairn(
                root,
                "update",
                "knowledge/deploy-403-token-rotation.md",
                "--append",
                "Verify workspace access after token rotation.",
            )

            self.assertEqual(init.returncode, 0, init.stderr)
            self.assertEqual(capture.returncode, 0, capture.stderr)
            self.assertEqual(index.returncode, 0, index.stderr)
            self.assertEqual(search.returncode, 0, search.stderr)
            self.assertEqual(retrieve.returncode, 0, retrieve.stderr)
            self.assertEqual(similar.returncode, 0, similar.stderr)
            self.assertEqual(update.returncode, 0, update.stderr)
            self.assertEqual(json.loads(search.stdout)[0]["path"], "knowledge/deploy-403-token-rotation.md")
            self.assertIn("heading: Resolution", retrieve.stdout)
            self.assertIn("Rotate the CI token.", retrieve.stdout)
            self.assertEqual(json.loads(similar.stdout)[0]["path"], "knowledge/deploy-403-token-rotation.md")
            self.assertIn("updated", update.stdout)


if __name__ == "__main__":
    unittest.main()
