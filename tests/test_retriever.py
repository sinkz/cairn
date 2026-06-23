from __future__ import annotations

import json
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

    def test_cli_retrieve_passages_uses_less_context_than_documents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "large.md",
                (
                    "type: Runbook",
                    "title: Large deploy note",
                    "description: Deploy troubleshooting.",
                    "tags: [deploy]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\n"
                + ("noise " * 200)
                + "\n\n# Resolution\n\nrotate token needle\n",
            )
            run_cairn(root, "index", "--rebuild")

            doc = run_cairn(root, "retrieve", "rotate token needle", "--budget", "800")
            passage = run_cairn(
                root,
                "retrieve",
                "rotate token needle",
                "--budget",
                "800",
                "--mode",
                "passages",
            )

            self.assertEqual(doc.returncode, 0, doc.stderr)
            self.assertEqual(passage.returncode, 0, passage.stderr)
            self.assertIn("heading: Resolution", passage.stdout)
            self.assertIn("rotate token needle", passage.stdout)
            self.assertLess(len(passage.stdout), len(doc.stdout))

    def test_cli_retrieve_json_returns_structured_context_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "deploy-403.md",
                (
                    "type: Runbook",
                    "title: Deploy 403",
                    "description: Fix deploy authorization failures.",
                    "tags: [deploy, bug]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nDeploy fails.\n\n# Resolution\n\nRotate the CI token.\n",
            )
            run_cairn(root, "index", "--rebuild")

            result = run_cairn(
                root,
                "retrieve",
                "rotate ci token",
                "--mode",
                "passages",
                "--budget",
                "300",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            packet = json.loads(result.stdout)
            self.assertEqual(packet["query"], "rotate ci token")
            self.assertEqual(packet["mode"], "passages")
            self.assertEqual(packet["budget_tokens"], 300)
            self.assertGreater(packet["used_tokens"], 0)
            self.assertEqual(packet["source_count"], 1)
            self.assertIn("Rotate the CI token.", packet["context"])
            self.assertEqual(packet["sources"][0]["path"], "knowledge/deploy-403.md")
            self.assertEqual(packet["sources"][0]["heading"], "Resolution")
            self.assertIn("score", packet["sources"][0])

    def test_cli_retrieve_json_explain_reports_source_explanations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "deploy-403.md",
                (
                    "type: Runbook",
                    "title: Deploy 403",
                    "description: Fix deploy authorization failures.",
                    "tags: [deploy, bug]",
                    "timestamp: 2026-06-17T10:00:00Z",
                    "signals: [http 403, ci token]",
                ),
                "# Resolution\n\nRotate the CI token and rerun the job.\n",
            )
            run_cairn(root, "index", "--rebuild")

            result = run_cairn(
                root,
                "retrieve",
                "deploy 403 token",
                "--mode",
                "passages",
                "--budget",
                "300",
                "--json",
                "--explain",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn("packet", payload)
            diagnostics = payload["query_diagnostics"]
            self.assertEqual(diagnostics["strict_query"], '"deploy" "403" "token"')
            self.assertEqual(diagnostics["zero_hit_terms"], [])
            self.assertEqual(diagnostics["relaxed_query"], "")
            self.assertFalse(diagnostics["relaxation_applied"])
            self.assertEqual(payload["packet"]["source_count"], 1)
            explanation = payload["explanations"][0]
            self.assertEqual(explanation["path"], "knowledge/deploy-403.md")
            self.assertEqual(explanation["heading"], "Resolution")
            self.assertIn("not confidence", explanation["score_note"])
            matched = {item["term"]: item["fields"] for item in explanation["matched_terms"]}
            self.assertIn("title", matched["deploy"])
            self.assertIn("signals", matched["token"])

    def test_cli_retrieve_json_explain_reports_zero_hit_relaxation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "deploy-credentials.md",
                (
                    "type: Runbook",
                    "title: Deploy credentials rotation",
                    "description: Update credentials for deployment jobs.",
                    "tags: [deploy, security]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Resolution\n\nRotate the deployment credentials and rerun the job.\n",
            )
            run_cairn(root, "index", "--rebuild")

            result = run_cairn(
                root,
                "retrieve",
                "credentials xyzzy",
                "--mode",
                "passages",
                "--budget",
                "300",
                "--json",
                "--explain",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            diagnostics = payload["query_diagnostics"]
            self.assertEqual(diagnostics["strict_query"], '"credentials" "xyzzy"')
            self.assertEqual(diagnostics["zero_hit_terms"], ["xyzzy"])
            self.assertEqual(diagnostics["relaxed_query"], '"credentials"')
            self.assertTrue(diagnostics["relaxation_applied"])
            self.assertEqual(payload["packet"]["sources"][0]["path"], "knowledge/deploy-credentials.md")

    def test_cli_retrieve_json_explain_abstains_for_stopword_only_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "formatting.md",
                (
                    "type: Decision",
                    "title: Use Ruff for formatting",
                    "description: Tooling decision for Python.",
                    "tags: [tooling]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nRuff is used for linting and formatting.\n",
            )
            run_cairn(root, "index", "--rebuild")

            result = run_cairn(root, "retrieve", "the", "--budget", "300", "--json", "--explain")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["packet"]["source_count"], 0)
            self.assertEqual(payload["packet"]["context"], "")
            diagnostics = payload["query_diagnostics"]
            self.assertEqual(diagnostics.get("reason"), "no_signal")
            self.assertFalse(diagnostics["relaxation_applied"])

    def test_cli_retrieve_json_explain_abstains_when_relaxation_drops_most_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "configuration.md",
                (
                    "type: Reference",
                    "title: Service configuration",
                    "description: Internal configuration notes.",
                    "tags: [infra]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nConfiguration values are managed by the platform team.\n",
            )
            run_cairn(root, "index", "--rebuild")

            result = run_cairn(
                root,
                "retrieve",
                "rocket engine cryogenic fuel configuration xyz",
                "--budget",
                "300",
                "--json",
                "--explain",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            diagnostics = payload["query_diagnostics"]
            self.assertIn("configuration", diagnostics["relaxed_query"])
            self.assertFalse(diagnostics["relaxation_applied"])
            self.assertEqual(payload["packet"]["source_count"], 0)
            self.assertEqual(payload["packet"]["context"], "")

    def test_cli_retrieve_accepts_rrf_ranker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "deploy-secret.md",
                (
                    "type: Runbook",
                    "title: Deploy token rotation",
                    "description: Update the CI secret after token rotation.",
                    "tags: [deploy, bug]",
                    "timestamp: 2026-06-17T10:00:00Z",
                    "signals: [deploy token rotation, ci secret]",
                ),
                "# Resolution\n\nUpdate the CI secret and rerun the failed deployment job.\n",
            )
            run_cairn(root, "index", "--rebuild")

            result = run_cairn(
                root,
                "retrieve",
                "deploy token rotation kubernetes secret",
                "--ranker",
                "rrf",
                "--budget",
                "400",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("knowledge/deploy-secret.md", result.stdout)
            self.assertIn("Update the CI secret", result.stdout)

    def test_cli_retrieve_auto_ranker_falls_back_to_rrf_documents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "deploy-secret.md",
                (
                    "type: Runbook",
                    "title: Deploy token rotation",
                    "description: Update the CI secret after token rotation.",
                    "tags: [deploy, bug]",
                    "timestamp: 2026-06-17T10:00:00Z",
                    "signals: [deploy token rotation, ci secret]",
                ),
                "# Resolution\n\nUpdate the CI secret and rerun the failed deployment job.\n",
            )
            write_concept(
                root,
                "kubernetes-noise.md",
                (
                    "type: Note",
                    "title: Kubernetes glossary",
                    "description: Background terms for cluster operations.",
                    "tags: [reference]",
                    "timestamp: 2026-06-17T10:00:00Z",
                    "signals: [kubernetes]",
                ),
                "# Context\n\nkubernetes kubernetes kubernetes background.\n",
            )
            run_cairn(root, "index", "--rebuild")

            result = run_cairn(
                root,
                "retrieve",
                "deploy token rotation kubernetes secret",
                "--ranker",
                "auto",
                "--budget",
                "400",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("knowledge/deploy-secret.md", result.stdout)
            self.assertIn("Update the CI secret", result.stdout)

    def test_cli_retrieve_passages_accepts_rrf_ranker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "cache-failover.md",
                (
                    "type: Runbook",
                    "title: Cache failover workers",
                    "description: Restore workers after cache failover.",
                    "tags: [cache, bug]",
                    "timestamp: 2026-06-17T10:00:00Z",
                    "signals: [cache failover]",
                ),
                "# Context\n\nWorkers stay disconnected after failover.\n\n"
                "# Resolution\n\nRun the reconnection workflow and restart affected workers.\n",
            )
            run_cairn(root, "index", "--rebuild")

            result = run_cairn(
                root,
                "retrieve",
                "reconnecting",
                "--mode",
                "passages",
                "--ranker",
                "rrf",
                "--budget",
                "250",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("knowledge/cache-failover.md", result.stdout)
            self.assertIn("heading: Resolution", result.stdout)
            self.assertIn("lines:", result.stdout)
            self.assertIn("reconnection workflow", result.stdout)

    def test_cli_retrieve_auto_ranker_falls_back_to_rrf_passages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "cache-failover.md",
                (
                    "type: Runbook",
                    "title: Cache failover workers",
                    "description: Restore workers after cache failover.",
                    "tags: [cache, bug]",
                    "timestamp: 2026-06-17T10:00:00Z",
                    "signals: [cache failover]",
                ),
                "# Context\n\nWorkers stay disconnected after failover.\n\n"
                "# Resolution\n\nRun the reconnection workflow and restart affected workers.\n",
            )
            run_cairn(root, "index", "--rebuild")

            result = run_cairn(
                root,
                "retrieve",
                "reconnecting",
                "--mode",
                "passages",
                "--ranker",
                "auto",
                "--budget",
                "250",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("knowledge/cache-failover.md", result.stdout)
            self.assertIn("heading: Resolution", result.stdout)
            self.assertIn("reconnection workflow", result.stdout)

    def test_cli_retrieve_redacts_secret_like_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            secret_value = "AKIAIOSFODNN7EXAMPLE"
            write_concept(
                root,
                "secret.md",
                (
                    "type: Runbook",
                    "title: Secret handling",
                    "description: Contains a fake access key for redaction.",
                    "tags: [bug]",
                    "timestamp: 2026-06-17T10:00:00Z",
                    "signals: [access key redaction]",
                ),
                "# Context\n\n"
                f"An AWS access key {secret_value} was accidentally pasted here.\n",
            )
            run_cairn(root, "index", "--rebuild")

            result = run_cairn(root, "retrieve", "access key redaction", "--budget", "400")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(secret_value, result.stdout)
            self.assertIn("[REDACTED:AWS access key]", result.stdout)


if __name__ == "__main__":
    unittest.main()
