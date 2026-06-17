from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cairn.vault import init_vault
from cairn.cli import main


class InitVaultTests(unittest.TestCase):
    def test_init_creates_profile_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = init_vault(root, profile_name="engineering")

            self.assertTrue((root / "AGENTS.md").exists())
            self.assertTrue((root / "SCHEMA.md").exists())
            self.assertTrue((root / "index.md").exists())
            self.assertTrue((root / "log.md").exists())
            self.assertTrue((root / ".cairn" / "config.json").exists())
            self.assertTrue((root / "_templates" / "concept.md").exists())
            self.assertTrue((root / "processes").is_dir())
            self.assertIn("AGENTS.md", result.created)

    def test_init_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            agents_path = root / "AGENTS.md"
            agents_path.write_text("custom guide\n", encoding="utf-8")

            result = init_vault(root, profile_name="personal")

            self.assertEqual(agents_path.read_text(encoding="utf-8"), "custom guide\n")
            self.assertIn("AGENTS.md", result.skipped)

    def test_cli_init_creates_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                try:
                    code = main(["init", "--path", tmp, "--profile", "support"])
                except SystemExit as exc:
                    code = exc.code if isinstance(exc.code, int) else 1

            self.assertEqual(code, 0, err.getvalue())
            self.assertTrue((Path(tmp) / "AGENTS.md").exists())
            self.assertIn("created AGENTS.md", out.getvalue())


if __name__ == "__main__":
    unittest.main()
