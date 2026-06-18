from __future__ import annotations

import hashlib
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


def run_cairn(cwd: Path, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env.setdefault("APOLLOKAIRN_REGISTRY_PATH", str(ROOT / ".cairn" / f"test-registry-{os.getpid()}.json"))
    return subprocess.run(
        [sys.executable, "-m", "cairn", *args],
        cwd=cwd,
        env=env,
        text=True,
        input=input_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class NotesTests(unittest.TestCase):
    def test_cli_add_creates_valid_note_with_slug(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")

            result = run_cairn(
                root,
                "add",
                "--title",
                "Deploy 403 Fix",
                "--type",
                "Runbook",
                "--description",
                "Fix deploy authorization failures.",
                "--tag",
                "bug",
                "--tag",
                "deploy",
                "--system",
                "ci",
                "--signal",
                "http 403",
                "--body",
                "Rotate the CI token and verify workspace access.",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("knowledge/deploy-403-fix.md", result.stdout)
            created = root / "knowledge" / "deploy-403-fix.md"
            self.assertTrue(created.is_file())
            text = created.read_text(encoding="utf-8")
            self.assertIn("type: Runbook", text)
            self.assertIn("tags: [bug, deploy]", text)
            self.assertIn("systems: [ci]", text)
            self.assertEqual(validate_vault(root).errors, [])

    def test_cli_capture_alias_creates_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")

            result = run_cairn(
                root,
                "capture",
                "--title",
                "Weekly workflow",
                "--description",
                "Personal workflow note.",
                "--tag",
                "workflow",
                "--body",
                "Review open loops every Friday.",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / "knowledge" / "weekly-workflow.md").is_file())

    def test_cli_capture_json_reports_created_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")

            result = run_cairn(
                root,
                "capture",
                "--title",
                "JSON capture",
                "--description",
                "Personal workflow note.",
                "--tag",
                "workflow",
                "--body",
                "Review open loops every Friday.",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["path"], "knowledge/json-capture.md")
            self.assertTrue(payload["changed"])
            self.assertTrue(payload["would_change"])
            self.assertFalse(payload["dry_run"])
            self.assertEqual(payload["reason"], "created")
            self.assertTrue(payload["sha256_after"])

    def test_cli_capture_dry_run_json_does_not_write_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")

            result = run_cairn(
                root,
                "capture",
                "--title",
                "Dry run capture",
                "--description",
                "Personal workflow note.",
                "--tag",
                "workflow",
                "--body",
                "Do not persist this.",
                "--dry-run",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["path"], "knowledge/dry-run-capture.md")
            self.assertFalse(payload["changed"])
            self.assertTrue(payload["would_change"])
            self.assertTrue(payload["dry_run"])
            self.assertEqual(payload["reason"], "dry_run")
            self.assertFalse((root / "knowledge" / "dry-run-capture.md").exists())

    def test_cli_capture_reads_body_file_and_preserves_markdown_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "vault"
            init_vault(root, profile_name="personal")
            body_file = base / "capture-body.md"
            body_file.write_text(
                "# Context\n\n"
                "Initial context from a file.\n\n"
                "# Resolution\n\n"
                "Use the documented file input path.\n",
                encoding="utf-8",
            )

            result = run_cairn(
                root,
                "capture",
                "--title",
                "File body capture",
                "--description",
                "A capture loaded from a Markdown file.",
                "--tag",
                "workflow",
                "--body-file",
                str(body_file),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            text = (root / "knowledge" / "file-body-capture.md").read_text(encoding="utf-8")
            self.assertEqual(text.count("# Context"), 1)
            self.assertIn("Initial context from a file.", text)
            self.assertIn("# Resolution", text)
            self.assertEqual(validate_vault(root).errors, [])

    def test_cli_capture_reads_body_from_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")

            result = run_cairn(
                root,
                "capture",
                "--title",
                "Stdin body capture",
                "--description",
                "A capture loaded from standard input.",
                "--tag",
                "workflow",
                "--body-stdin",
                input_text="# Context\n\nBody read from stdin.\n",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            text = (root / "knowledge" / "stdin-body-capture.md").read_text(encoding="utf-8")
            self.assertIn("Body read from stdin.", text)
            self.assertEqual(text.count("# Context"), 1)

    def test_cli_capture_rejects_schema_policy_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")

            result = run_cairn(
                root,
                "capture",
                "--title",
                "Invalid policy note",
                "--description",
                "Should not be written.",
                "--type",
                "Runbook",
                "--tag",
                "deploy",
                "--body",
                "This type and tag are not part of the personal schema.",
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("type 'Runbook' is not declared in SCHEMA.md", result.stderr)
            self.assertIn("tag 'deploy' is not declared in SCHEMA.md", result.stderr)
            self.assertFalse((root / "knowledge" / "invalid-policy-note.md").exists())

    def test_cli_capture_dry_run_json_reports_schema_policy_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")

            result = run_cairn(
                root,
                "capture",
                "--title",
                "Invalid policy preview",
                "--description",
                "Should not be written.",
                "--type",
                "Runbook",
                "--tag",
                "deploy",
                "--body",
                "Preview invalid policy output.",
                "--dry-run",
                "--json",
            )

            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["error_count"], 2)
            self.assertEqual(payload["path"], "knowledge/invalid-policy-preview.md")
            messages = "\n".join(issue["message"] for issue in payload["errors"])
            self.assertIn("type 'Runbook'", messages)
            self.assertIn("tag 'deploy'", messages)
            self.assertFalse((root / "knowledge" / "invalid-policy-preview.md").exists())

    def test_cli_capture_rejects_secret_like_value_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            secret_value = "AKIAIOSFODNN7EXAMPLE"

            result = run_cairn(
                root,
                "capture",
                "--title",
                "Secret capture",
                "--description",
                "Should be blocked before writing.",
                "--type",
                "Runbook",
                "--tag",
                "bug",
                "--body",
                f"Do not store AWS access key {secret_value} in notes.",
                "--json",
            )

            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            messages = "\n".join(issue["message"] for issue in payload["errors"])
            self.assertIn("potential secret", messages)
            self.assertIn("AWS access key", messages)
            self.assertNotIn(secret_value, messages)
            self.assertFalse((root / "knowledge" / "secret-capture.md").exists())

    def test_cli_add_rejects_folder_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            init_vault(root, profile_name="personal")

            result = run_cairn(
                root,
                "add",
                "--title",
                "Outside",
                "--description",
                "Should not escape the vault.",
                "--tag",
                "personal",
                "--folder",
                "..",
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("path must stay inside vault", result.stderr)
            self.assertFalse((root.parent / "outside.md").exists())

    def test_cli_update_appends_text_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            run_cairn(
                root,
                "add",
                "--title",
                "Support handoff",
                "--description",
                "Workflow note.",
                "--tag",
                "workflow",
                "--body",
                "Initial note.",
            )

            first = run_cairn(root, "update", "knowledge/support-handoff.md", "--append", "Add reproduction steps.")
            second = run_cairn(root, "update", "knowledge/support-handoff.md", "--append", "Add reproduction steps.")

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            text = (root / "knowledge" / "support-handoff.md").read_text(encoding="utf-8")
            self.assertEqual(text.count("Add reproduction steps."), 1)
            self.assertIn("unchanged", second.stdout)

    def test_cli_update_json_reports_noop_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            run_cairn(
                root,
                "add",
                "--title",
                "Support handoff",
                "--description",
                "Workflow note.",
                "--tag",
                "workflow",
                "--body",
                "Initial note.",
            )

            run_cairn(root, "update", "knowledge/support-handoff.md", "--append", "Already documented.")
            result = run_cairn(
                root,
                "update",
                "knowledge/support-handoff.md",
                "--append",
                "Already documented.",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["path"], "knowledge/support-handoff.md")
            self.assertFalse(payload["changed"])
            self.assertFalse(payload["would_change"])
            self.assertEqual(payload["reason"], "already_present")

    def test_cli_update_dry_run_json_does_not_write_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            run_cairn(
                root,
                "add",
                "--title",
                "Incident checklist",
                "--description",
                "Reusable incident checklist.",
                "--tag",
                "workflow",
                "--body",
                "Initial note.",
            )

            result = run_cairn(
                root,
                "update",
                "knowledge/incident-checklist.md",
                "--append",
                "Confirm customer impact before escalation.",
                "--dry-run",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["changed"])
            self.assertTrue(payload["would_change"])
            self.assertTrue(payload["dry_run"])
            self.assertEqual(payload["reason"], "dry_run")
            text = (root / "knowledge" / "incident-checklist.md").read_text(encoding="utf-8")
            self.assertNotIn("Confirm customer impact before escalation.", text)

    def test_cli_update_rejects_stale_expected_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            run_cairn(
                root,
                "add",
                "--title",
                "Access approval",
                "--description",
                "How to request approval.",
                "--tag",
                "workflow",
                "--body",
                "Initial note.",
            )
            note = root / "knowledge" / "access-approval.md"
            current_hash = hashlib.sha256(note.read_bytes()).hexdigest()
            note.write_text(note.read_text(encoding="utf-8") + "\nConcurrent edit.\n", encoding="utf-8")

            result = run_cairn(
                root,
                "update",
                "knowledge/access-approval.md",
                "--append",
                "Should not write.",
                "--expect-sha256",
                current_hash,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("modified since expected sha256", result.stderr)
            self.assertNotIn("Should not write.", note.read_text(encoding="utf-8"))

    def test_cli_update_rejects_secret_like_value_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            run_cairn(
                root,
                "add",
                "--title",
                "Deploy runbook",
                "--description",
                "Reusable deploy runbook.",
                "--type",
                "Runbook",
                "--tag",
                "deploy",
                "--body",
                "Initial note.",
            )
            secret_value = "AKIAIOSFODNN7EXAMPLE"

            result = run_cairn(
                root,
                "update",
                "knowledge/deploy-runbook.md",
                "--append",
                f"Do not store AWS access key {secret_value} in notes.",
                "--json",
            )

            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["path"], "knowledge/deploy-runbook.md")
            messages = "\n".join(issue["message"] for issue in payload["errors"])
            self.assertIn("potential secret", messages)
            self.assertIn("AWS access key", messages)
            self.assertNotIn(secret_value, messages)
            text = (root / "knowledge" / "deploy-runbook.md").read_text(encoding="utf-8")
            self.assertNotIn(secret_value, text)

    def test_cli_update_appends_file_accepts_absolute_path_and_touches_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "vault"
            init_vault(root, profile_name="personal")
            run_cairn(
                root,
                "add",
                "--title",
                "Access approval",
                "--description",
                "How to request approval.",
                "--tag",
                "workflow",
                "--timestamp",
                "2000-01-01T00:00:00Z",
                "--body",
                "Initial note.",
            )
            note = root / "knowledge" / "access-approval.md"
            append_file = base / "append.md"
            append_file.write_text("# Latest Check\n\nAsk the owner to approve the request.\n", encoding="utf-8")

            result = run_cairn(root, "update", str(note), "--append-file", str(append_file))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("updated knowledge/access-approval.md", result.stdout)
            text = note.read_text(encoding="utf-8")
            self.assertIn("# Latest Check", text)
            self.assertIn("Ask the owner to approve the request.", text)
            self.assertNotIn("timestamp: 2000-01-01T00:00:00Z", text)

    def test_cli_update_reads_append_from_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            run_cairn(
                root,
                "add",
                "--title",
                "Incident checklist",
                "--description",
                "Reusable incident checklist.",
                "--tag",
                "workflow",
                "--body",
                "Initial note.",
            )

            result = run_cairn(
                root,
                "update",
                "knowledge/incident-checklist.md",
                "--append-stdin",
                input_text="Confirm customer impact before escalation.\n",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            text = (root / "knowledge" / "incident-checklist.md").read_text(encoding="utf-8")
            self.assertIn("Confirm customer impact before escalation.", text)

    def test_cli_update_rejects_absolute_path_outside_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "vault"
            outside = base / "outside.md"
            init_vault(root, profile_name="personal")
            outside.write_text("# outside\n", encoding="utf-8")

            result = run_cairn(root, "update", str(outside), "--append", "Should not write.")

            self.assertEqual(result.returncode, 1)
            self.assertIn("path must stay inside vault", result.stderr)
            self.assertNotIn("Should not write.", outside.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
