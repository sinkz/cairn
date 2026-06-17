from __future__ import annotations

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
            self.assertIn("possible duplicate", result.stdout)


if __name__ == "__main__":
    unittest.main()
