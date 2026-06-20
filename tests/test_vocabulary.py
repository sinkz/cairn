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

from cairn.indexer import rebuild_index, search
from cairn.retriever import retrieve_packet
from cairn.validate import validate_vault
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


def write_k8s_note(root: Path) -> None:
    (root / "knowledge" / "rollback-k8s.md").write_text(
        "---\n"
        "type: Runbook\n"
        "title: Rollback rapido deploy K8s\n"
        "description: Procedimento de rollback para deploy em cluster.\n"
        "tags: [deploy, bug]\n"
        "timestamp: 2026-06-18T00:00:00Z\n"
        "systems: [platform]\n"
        "---\n\n"
        "# Context\n\n"
        "Use quando o deploy em k8s precisa voltar rapido.\n",
        encoding="utf-8",
    )


def write_literal_kubernetes_note(root: Path) -> None:
    (root / "knowledge" / "kubernetes-reference.md").write_text(
        "---\n"
        "type: Knowledge\n"
        "title: Kubernetes deploy rollback reference\n"
        "description: Background reference that uses the long Kubernetes name.\n"
        "tags: [deploy, reference]\n"
        "timestamp: 2026-06-18T00:00:00Z\n"
        "systems: [platform]\n"
        "---\n\n"
        "# Context\n\n"
        "Kubernetes deploy rollback terminology and general background.\n",
        encoding="utf-8",
    )


def write_glossary(root: Path) -> None:
    (root / "glossary.md").write_text(
        "# Glossary\n\n"
        "## Kubernetes\n\n"
        "aliases: k8s, kube\n"
        "status: approved\n"
        "scope: engineering\n\n"
        "## Rollback\n\n"
        "aliases: reversao, reverter, voltar versao\n"
        "status: approved\n",
        encoding="utf-8",
    )


class VocabularyTests(unittest.TestCase):
    def test_search_uses_approved_glossary_alias_when_exact_query_misses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_glossary(root)
            write_k8s_note(root)
            rebuild_index(root)

            results = search(root, "kubernetes rollback emergencial deploy", limit=3)

            self.assertEqual([result.path for result in results], ["knowledge/rollback-k8s.md"])

    def test_search_uses_approved_glossary_alias_when_exact_query_already_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_glossary(root)
            write_k8s_note(root)
            write_literal_kubernetes_note(root)
            rebuild_index(root)

            results = search(root, "kubernetes rollback deploy", limit=3)

            paths = [result.path for result in results]
            self.assertIn("knowledge/kubernetes-reference.md", paths)
            self.assertIn("knowledge/rollback-k8s.md", paths)

    def test_search_does_not_or_separate_glossary_groups(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_glossary(root)
            (root / "knowledge" / "k8s-only.md").write_text(
                "---\n"
                "type: Note\n"
                "title: K8s cluster reference\n"
                "description: Cluster notes.\n"
                "tags: [reference]\n"
                "timestamp: 2026-06-18T00:00:00Z\n"
                "---\n\n"
                "# Context\n\nK8s cluster operations.\n",
                encoding="utf-8",
            )
            (root / "knowledge" / "oauth-only.md").write_text(
                "---\n"
                "type: Note\n"
                "title: OAuth reference\n"
                "description: Identity provider notes.\n"
                "tags: [reference]\n"
                "timestamp: 2026-06-18T00:00:00Z\n"
                "---\n\n"
                "# Context\n\nOAuth identity provider operations.\n",
                encoding="utf-8",
            )
            rebuild_index(root)

            results = search(root, "kubernetes oauth", limit=3)

            self.assertEqual(results, [])

    def test_search_rrf_uses_approved_glossary_alias_when_exact_query_already_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_glossary(root)
            write_k8s_note(root)
            write_literal_kubernetes_note(root)
            rebuild_index(root)

            results = search(root, "kubernetes", limit=3, ranker="rrf")

            paths = [result.path for result in results]
            self.assertIn("knowledge/kubernetes-reference.md", paths)
            self.assertIn("knowledge/rollback-k8s.md", paths)

    def test_search_explain_reports_approved_glossary_alias_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_glossary(root)
            write_k8s_note(root)
            rebuild_index(root)

            result = run_cairn(
                root,
                "search",
                "kubernetes rollback emergencial deploy",
                "--json",
                "--explain",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            diagnostics = payload["query_diagnostics"]
            self.assertEqual(diagnostics["zero_hit_terms"], ["emergencial"])
            self.assertIn('"k8s"', diagnostics["relaxed_query"])
            self.assertNotIn('"emergencial"', diagnostics["relaxed_query"])
            explanation = payload["results"][0]["explanation"]
            matched = {item["term"]: item["fields"] for item in explanation["matched_terms"]}
            self.assertIn("k8s", matched)
            self.assertIn("title", matched["k8s"])

    def test_retrieve_auto_uses_glossary_aliases_for_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_glossary(root)
            write_k8s_note(root)
            rebuild_index(root)

            packet = retrieve_packet(
                root,
                "kubernetes rollback emergencial deploy",
                ranker="auto",
                budget_tokens=500,
            )

            self.assertEqual(packet.ranker, "bm25")
            self.assertEqual(packet.source_count, 1)
            self.assertEqual(packet.sources[0].path, "knowledge/rollback-k8s.md")
            self.assertIn("Rollback rapido deploy K8s", packet.context)

    def test_retrieve_passages_uses_approved_glossary_alias_when_exact_query_already_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_glossary(root)
            write_k8s_note(root)
            write_literal_kubernetes_note(root)
            rebuild_index(root)

            packet = retrieve_packet(
                root,
                "kubernetes rollback deploy",
                mode="passages",
                ranker="bm25",
                limit=3,
                budget_tokens=500,
            )

            paths = [source.path for source in packet.sources]
            self.assertIn("knowledge/kubernetes-reference.md", paths)
            self.assertIn("knowledge/rollback-k8s.md", paths)

    def test_retrieve_passages_rrf_uses_approved_glossary_alias_when_exact_query_already_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_glossary(root)
            write_k8s_note(root)
            write_literal_kubernetes_note(root)
            rebuild_index(root)

            packet = retrieve_packet(
                root,
                "kubernetes",
                mode="passages",
                ranker="rrf",
                limit=3,
                budget_tokens=500,
            )

            paths = [source.path for source in packet.sources]
            self.assertIn("knowledge/kubernetes-reference.md", paths)
            self.assertIn("knowledge/rollback-k8s.md", paths)

    def test_vocab_add_term_and_validate_manage_glossary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")

            add = run_cairn(root, "vocab", "add-term", "Kubernetes", "--alias", "k8s", "--alias", "kube")
            validate = run_cairn(root, "vocab", "validate", "--json")

            self.assertEqual(add.returncode, 0, add.stderr)
            self.assertEqual(validate.returncode, 0, validate.stderr)
            glossary = (root / "glossary.md").read_text(encoding="utf-8")
            self.assertIn("## Kubernetes", glossary)
            self.assertIn("aliases: k8s, kube", glossary)
            payload = json.loads(validate.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["term_count"], 1)
            self.assertEqual(payload["alias_count"], 2)

    def test_vocab_add_term_json_reports_term(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")

            result = run_cairn(root, "vocab", "add-term", "Kubernetes", "--alias", "k8s", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["title"], "Kubernetes")
            self.assertEqual(payload["aliases"], ["k8s"])
            self.assertEqual(payload["status"], "approved")

    def test_vocab_add_alias_updates_existing_term(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            run_cairn(root, "vocab", "add-term", "Kubernetes", "--alias", "k8s")

            result = run_cairn(root, "vocab", "add-alias", "Kubernetes", "kube")

            self.assertEqual(result.returncode, 0, result.stderr)
            glossary = (root / "glossary.md").read_text(encoding="utf-8")
            self.assertIn("aliases: k8s, kube", glossary)

    def test_vocab_add_alias_json_reports_updated_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            run_cairn(root, "vocab", "add-term", "Kubernetes", "--alias", "k8s")

            result = run_cairn(root, "vocab", "add-alias", "Kubernetes", "kube", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["aliases"], ["k8s", "kube"])

    def test_vocab_suggest_reports_candidates_without_writing_glossary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_k8s_note(root)

            result = run_cairn(
                root,
                "vocab",
                "suggest",
                "kubernetes rollback emergencial deploy",
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["query"], "kubernetes rollback emergencial deploy")
            self.assertFalse((root / "glossary.md").exists())
            self.assertGreaterEqual(len(payload["suggestions"]), 1)
            suggestion = payload["suggestions"][0]
            self.assertEqual(suggestion["term"], "kubernetes")
            self.assertEqual(suggestion["alias"], "k8s")
            self.assertEqual(suggestion["path"], "knowledge/rollback-k8s.md")
            self.assertIn("shared terms", " ".join(suggestion["evidence"]))

    def test_vocab_lookup_json_reports_registered_aliases_for_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_glossary(root)

            result = run_cairn(root, "vocab", "lookup", "k8s rollback", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["query"], "k8s rollback")
            matches = {item["term"]: item for item in payload["matches"]}
            self.assertEqual(matches["Kubernetes"]["aliases"], ["k8s", "kube"])
            self.assertEqual(matches["Kubernetes"]["matched"], ["k8s"])
            self.assertEqual(matches["Kubernetes"]["expansion"], ["Kubernetes", "k8s", "kube"])
            self.assertEqual(matches["Rollback"]["matched"], ["Rollback"])

    def test_vocab_lookup_json_only_reports_approved_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            (root / "glossary.md").write_text(
                "# Glossary\n\n"
                "## Forbidden\n\n"
                "aliases: access denied, denied\n"
                "status: approved\n\n"
                "## Draft Secret\n\n"
                "aliases: xyzzy\n"
                "status: draft\n",
                encoding="utf-8",
            )

            result = run_cairn(root, "vocab", "lookup", "access denied xyzzy", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual([item["term"] for item in payload["matches"]], ["Forbidden"])
            self.assertIn("access denied", payload["matches"][0]["matched"])
            self.assertNotIn("Draft Secret", [item["term"] for item in payload["matches"]])

    def test_glossary_is_reserved_and_does_not_break_vault_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_glossary(root)

            report = validate_vault(root)

            self.assertEqual(report.errors, [])


if __name__ == "__main__":
    unittest.main()
