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

from cairn.validate import validate_vault
from cairn.vault import init_vault


VALID_FRONTMATTER = (
    "type: Note",
    "title: Demo",
    "description: A valid note.",
    "tags: [personal]",
    "timestamp: 2026-06-17T10:00:00Z",
)


def write_concept(root: Path, name: str, frontmatter: tuple[str, ...]) -> Path:
    concept = root / "knowledge" / name
    concept.write_text(
        "---\n" + "\n".join(frontmatter) + "\n---\n\n# Context\n",
        encoding="utf-8",
    )
    return concept


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


class ValidateTests(unittest.TestCase):
    def test_initialized_vault_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_concept(root, "demo.md", VALID_FRONTMATTER)

            report = validate_vault(root)

            self.assertEqual(report.errors, [])

    def test_invalid_type_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_concept(
                root,
                "bad.md",
                (
                    "type: Unknown",
                    "title: Bad",
                    "description: Bad note.",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
            )

            report = validate_vault(root)

            self.assertEqual(len(report.errors), 1)
            self.assertIn("type", report.errors[0].message)

    def test_required_scalar_fields_must_be_non_empty_strings(self) -> None:
        replacements = {
            "type": "type: [Note]",
            "title": "title: [Demo]",
            "description": "description: [A valid note.]",
            "timestamp": "timestamp: [2026-06-17T10:00:00Z]",
        }
        for field_name, replacement in replacements.items():
            with self.subTest(field=field_name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                init_vault(root, profile_name="personal")
                frontmatter = tuple(
                    replacement if line.startswith(f"{field_name}:") else line
                    for line in VALID_FRONTMATTER
                )
                write_concept(root, "bad-shape.md", frontmatter)

                report = validate_vault(root)

                self.assertEqual(len(report.errors), 1)
                self.assertIn(field_name, report.errors[0].message)
                self.assertIn("string", report.errors[0].message)

    def test_missing_required_field_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_concept(
                root,
                "missing.md",
                (
                    "type: Note",
                    "title: Demo",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
            )

            report = validate_vault(root)

            self.assertEqual(len(report.errors), 1)
            self.assertIn("missing required field: description", report.errors[0].message)

    def test_invalid_tag_is_error_even_when_schema_declares_no_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            (root / "SCHEMA.md").write_text(
                "# ApolloKairn Schema\n\n"
                "Profile: `custom`\n\n"
                "## Types\n\n"
                "- Note\n\n"
                "## Tags\n\n",
                encoding="utf-8",
            )
            write_concept(root, "bad-tag.md", VALID_FRONTMATTER)

            report = validate_vault(root)

            self.assertEqual(len(report.errors), 1)
            self.assertIn("tag 'personal'", report.errors[0].message)

    def test_invalid_timestamp_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_concept(
                root,
                "bad-time.md",
                (
                    "type: Note",
                    "title: Demo",
                    "description: A valid note.",
                    "tags: [personal]",
                    "timestamp: not-a-date",
                ),
            )

            report = validate_vault(root)

            self.assertEqual(len(report.errors), 1)
            self.assertIn("timestamp", report.errors[0].message)

    def test_frontmatter_parse_error_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            (root / "knowledge" / "plain.md").write_text("# Plain note\n", encoding="utf-8")

            report = validate_vault(root)

            self.assertEqual(len(report.errors), 1)
            self.assertIn("missing YAML frontmatter block", report.errors[0].message)

    def test_reserved_and_generated_files_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            (root / "index.md").write_text("# No frontmatter\n", encoding="utf-8")
            (root / "log.md").write_text("# No frontmatter\n", encoding="utf-8")
            (root / "README.md").write_text("# No frontmatter\n", encoding="utf-8")
            (root / "HERMES.md").write_text("# No frontmatter\n", encoding="utf-8")
            (root / "OPENCODE.md").write_text("# No frontmatter\n", encoding="utf-8")
            (root / ".github").mkdir()
            (root / ".github" / "copilot-instructions.md").write_text("# No frontmatter\n", encoding="utf-8")
            (root / "_templates" / "ignored.md").write_text("# No frontmatter\n", encoding="utf-8")
            (root / ".cairn" / "ignored.md").write_text("# No frontmatter\n", encoding="utf-8")

            report = validate_vault(root)

            self.assertEqual(report.errors, [])

    def test_config_excluded_folders_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            (root / "inbox" / "draft.md").write_text("# No frontmatter\n", encoding="utf-8")

            report = validate_vault(root)

            self.assertEqual(report.errors, [])

    def test_validate_flags_secret_like_values_without_echoing_them(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            secret_value = "AKIAIOSFODNN7EXAMPLE"
            (root / "knowledge" / "secret.md").write_text(
                "---\n"
                "type: Runbook\n"
                "title: Secret example\n"
                "description: Should be blocked.\n"
                "tags: [bug]\n"
                "timestamp: 2026-06-17T10:00:00Z\n"
                "---\n\n"
                "# Context\n\n"
                f"Do not store AWS access key {secret_value} in notes.\n",
                encoding="utf-8",
            )

            report = validate_vault(root)

            messages = "\n".join(issue.message for issue in report.errors)
            self.assertIn("potential secret", messages)
            self.assertIn("AWS access key", messages)
            self.assertNotIn(secret_value, messages)

    def test_cli_validate_returns_nonzero_and_prints_error_for_invalid_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_concept(
                root,
                "bad.md",
                (
                    "type: Unknown",
                    "title: Bad",
                    "description: Bad note.",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
            )

            result = run_cairn(root, "validate")

            self.assertEqual(result.returncode, 1)
            self.assertIn("ERROR knowledge/bad.md:", result.stdout)
            self.assertIn("type", result.stdout)

    def test_cli_validate_json_returns_issue_lists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_concept(
                root,
                "bad.md",
                (
                    "type: Unknown",
                    "title: Bad",
                    "description: Bad note.",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
            )

            result = run_cairn(root, "validate", "--json")

            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["error_count"], 1)
            self.assertEqual(payload["warning_count"], 0)
            self.assertEqual(payload["errors"][0]["path"], "knowledge/bad.md")
            self.assertIn("type", payload["errors"][0]["message"])

    def test_cli_validate_returns_zero_for_valid_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_concept(root, "demo.md", VALID_FRONTMATTER)

            result = run_cairn(root, "validate")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")

    def test_cli_validate_path_validates_vault_from_outside_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "vault"
            outside = base / "outside"
            outside.mkdir()
            init_vault(root, profile_name="personal")
            write_concept(root, "demo.md", VALID_FRONTMATTER)

            result = run_cairn(outside, "validate", "--path", str(root))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
