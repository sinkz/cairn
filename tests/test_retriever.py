from __future__ import annotations

import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cairn.vault import init_vault


def write_concept(root: Path, name: str, frontmatter: tuple[str, ...], body: str) -> Path:
    concept = root / "knowledge" / name
    concept.write_text(
        "---\n" + "\n".join(frontmatter) + "\n---\n\n" + body,
        encoding="utf-8",
    )
    return concept


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


class RetrieverTests(unittest.TestCase):
    def test_cli_retrieve_respects_budget_and_avoids_opening_every_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "vault"
            outside = base / "outside"
            outside.mkdir()
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "alpha.md",
                (
                    "type: Runbook",
                    "title: Alpha needle",
                    "description: Primary needle document.",
                    "tags: [bug]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nneedle PRIMARY_DETAIL " + ("alpha detail " * 80),
            )
            write_concept(
                root,
                "beta.md",
                (
                    "type: Runbook",
                    "title: Beta needle",
                    "description: Secondary needle document.",
                    "tags: [bug]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nneedle SECOND_BODY_SHOULD_NOT_APPEAR " + ("beta detail " * 80),
            )
            run_cairn(outside, "index", "--path", str(root), "--rebuild")

            result = run_cairn(
                outside,
                "retrieve",
                "needle",
                "--path",
                str(root),
                "--limit",
                "2",
                "--budget",
                "120",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertLessEqual(math.ceil(len(result.stdout) / 4), 120)
            self.assertIn("knowledge/alpha.md", result.stdout)
            self.assertIn("PRIMARY_DETAIL", result.stdout)
            self.assertNotIn("SECOND_BODY_SHOULD_NOT_APPEAR", result.stdout)


if __name__ == "__main__":
    unittest.main()
