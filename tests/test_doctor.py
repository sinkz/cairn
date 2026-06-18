from __future__ import annotations

import json
import os
import sqlite3
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


def write_note(root: Path, body: str = "doctorneedle") -> Path:
    path = root / "knowledge" / "doctor.md"
    path.write_text(
        "---\n"
        "type: Note\n"
        "title: Doctor note\n"
        "description: Health check note.\n"
        "tags: [personal]\n"
        "timestamp: 2026-06-17T10:00:00Z\n"
        "---\n\n"
        f"# Context\n\n{body}\n",
        encoding="utf-8",
    )
    return path


class DoctorTests(unittest.TestCase):
    def test_cli_doctor_reports_missing_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_note(root)

            result = run_cairn(root, "doctor")

            self.assertEqual(result.returncode, 1)
            self.assertIn("ERROR index missing", result.stdout)

    def test_cli_doctor_reports_fresh_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_note(root)
            run_cairn(root, "index", "--rebuild")

            result = run_cairn(root, "doctor")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("OK index fresh", result.stdout)

    def test_cli_doctor_json_returns_health_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_note(root)
            run_cairn(root, "index", "--rebuild")

            result = run_cairn(root, "doctor", "--json")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"])
            self.assertIn("OK config", payload["lines"])
            self.assertIn("OK validation", payload["lines"])
            self.assertIn("OK index fresh", payload["lines"])

    def test_cli_doctor_reports_stale_index_after_file_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            note = write_note(root)
            run_cairn(root, "index", "--rebuild")
            note.write_text(note.read_text(encoding="utf-8").replace("doctorneedle", "changedneedle"), encoding="utf-8")

            result = run_cairn(root, "doctor")

            self.assertEqual(result.returncode, 1)
            self.assertIn("STALE index", result.stdout)
            self.assertIn("changed 1", result.stdout)

    def test_cli_doctor_reports_incomplete_index_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_note(root)
            run_cairn(root, "index", "--rebuild")
            con = sqlite3.connect(root / ".cairn" / "index.db")
            try:
                con.execute("DROP TABLE passages")
                con.commit()
            finally:
                con.close()

            result = run_cairn(root, "doctor")

            self.assertEqual(result.returncode, 1)
            self.assertIn("ERROR index invalid", result.stdout)


if __name__ == "__main__":
    unittest.main()
