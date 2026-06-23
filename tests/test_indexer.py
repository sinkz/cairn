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

from cairn.indexer import CairnIndexError, rebuild_index, search, search_passages, show
from cairn.vault import init_vault


def write_concept(
    root: Path,
    name: str,
    frontmatter: tuple[str, ...],
    body: str = "# Context\n\nBody.\n",
) -> Path:
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


class IndexerTests(unittest.TestCase):
    def test_search_returns_matching_snippet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            concept = root / "knowledge" / "deploy-403.md"
            concept.write_text(
                "---\n"
                "type: Runbook\n"
                "title: Fix deploy 403\n"
                "description: Fix deploy when permission returns 403.\n"
                "tags: [deploy, bug]\n"
                "timestamp: 2026-06-17T10:00:00Z\n"
                "signals: [HTTP 403, permission denied]\n"
                "---\n\n"
                "# Context\n\n"
                "Deploy fails with HTTP 403 during release.\n",
                encoding="utf-8",
            )
            rebuild_index(root)

            results = search(root, "HTTP 403 deploy", limit=3)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].path, "knowledge/deploy-403.md")
            self.assertIn("403", results[0].snippet)

    def test_punctuation_heavy_query_does_not_crash_and_finds_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "deploy-403.md",
                (
                    "type: Runbook",
                    "title: Fix deploy-403 for C++ api/foo",
                    "description: title:deploy should still be searchable.",
                    "tags: [deploy, bug]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nC++ api/foo deployment fails with 403.\n",
            )
            rebuild_index(root)

            results = search(root, "deploy-403 C++ api/foo title:deploy", limit=3)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].path, "knowledge/deploy-403.md")

    def test_search_matches_portuguese_terms_without_accents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="support")
            write_concept(
                root,
                "autenticacao.md",
                (
                    "type: Procedure",
                    "title: Falha de autenticação",
                    "description: Corrige renovação de sessão no atendimento.",
                    "tags: [suporte, processo]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nUsuário não consegue renovar a sessão.\n",
            )
            rebuild_index(root)

            results = search(root, "autenticacao renovacao sessao", limit=3)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].path, "knowledge/autenticacao.md")

    def test_operator_words_do_not_become_required_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "deploy-403.md",
                (
                    "type: Runbook",
                    "title: Fix deploy 403",
                    "description: Permission failure.",
                    "tags: [deploy, bug]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nDeploy fails with HTTP 403 during release.\n",
            )
            rebuild_index(root)

            results = search(root, "deploy AND 403", limit=3)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].path, "knowledge/deploy-403.md")

    def test_title_match_ranks_above_repeated_body_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "body-noise.md",
                (
                    "type: Runbook",
                    "title: Body noise",
                    "description: Repeated body-only match.",
                    "tags: [bug]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\n" + ("rankneedle " * 40),
            )
            write_concept(
                root,
                "title-signal.md",
                (
                    "type: Runbook",
                    "title: rankneedle exact title",
                    "description: Title carries the primary signal.",
                    "tags: [bug]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nNo repeated body match.\n",
            )
            rebuild_index(root)

            results = search(root, "rankneedle", limit=2)

            self.assertEqual(results[0].path, "knowledge/title-signal.md")

    def test_rrf_search_recovers_when_query_contains_extra_terms(self) -> None:
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
            rebuild_index(root)

            default_results = search(root, "deploy token rotation kubernetes secret", limit=3)
            fused_results = search(root, "deploy token rotation kubernetes secret", limit=3, ranker="rrf")

            self.assertEqual(default_results, [])
            self.assertEqual(fused_results[0].path, "knowledge/deploy-secret.md")

    def test_bm25_search_relaxes_only_zero_hit_terms(self) -> None:
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
                    "signals: [credentials rotation]",
                ),
                "# Resolution\n\nRotate the deployment credentials and rerun the job.\n",
            )
            rebuild_index(root)

            results = search(root, "credentials xyzzy", limit=3)

            self.assertEqual([result.path for result in results], ["knowledge/deploy-credentials.md"])

    def test_bm25_search_does_not_or_terms_that_exist_separately(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "deploy.md",
                (
                    "type: Runbook",
                    "title: Deploy credentials",
                    "description: Deploy credentials procedure.",
                    "tags: [deploy]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nCredentials handling for deployment.\n",
            )
            write_concept(
                root,
                "oauth.md",
                (
                    "type: Note",
                    "title: OAuth reference",
                    "description: OAuth background.",
                    "tags: [reference]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nOAuth background for identity providers.\n",
            )
            rebuild_index(root)

            results = search(root, "credentials oauth", limit=3)

            self.assertEqual(results, [])

    def test_bm25_search_does_not_relax_to_stopword(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "clock-skew.md",
                (
                    "type: Runbook",
                    "title: Clock skew in JWT validation",
                    "description: Token timestamp drift in auth.",
                    "tags: [auth]",
                    "timestamp: 2026-06-17T10:00:00Z",
                    "signals: [iat in future]",
                ),
                "# Context\n\nJWT timestamps appear in the future when clocks drift.\n",
            )
            rebuild_index(root)

            results = search(root, "best hiking trails in patagonia", limit=3)

            self.assertEqual(results, [])

    def test_bm25_search_abstains_for_stopword_only_query(self) -> None:
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
            rebuild_index(root)

            result = run_cairn(root, "search", "the", "--json", "--explain")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["results"], [])
            diagnostics = payload["query_diagnostics"]
            self.assertEqual(diagnostics.get("reason"), "no_signal")
            self.assertFalse(diagnostics["relaxation_applied"])

    def test_bm25_search_relaxes_by_candidate_cooccurrence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="custom")
            write_concept(
                root,
                "horas-in-itinere.md",
                (
                    "type: Jurisprudencia",
                    "title: Horas in itinere apos reforma trabalhista",
                    "description: Tese sobre deslocamento e jornada.",
                    "tags: [trabalhista, tese]",
                    "timestamp: 2026-06-22T00:00:00Z",
                    "signals: [tempo de deslocamento]",
                ),
                "# Context\n\n"
                "Apos a reforma, o tempo de deslocamento casa-trabalho "
                "deixou de ser computado como jornada.\n",
            )
            write_concept(
                root,
                "prazo-recurso.md",
                (
                    "type: Procedimento",
                    "title: Prazo de recurso ordinario trabalhista",
                    "description: Prazo e contagem para interpor recurso.",
                    "tags: [prazo, recurso, trabalhista]",
                    "timestamp: 2026-06-22T00:00:00Z",
                ),
                "# Context\n\nConta-se o prazo a partir da intimacao.\n",
            )
            rebuild_index(root)

            result = run_cairn(
                root,
                "search",
                "deslocamento casa trabalho conta como jornada",
                "--json",
                "--explain",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertGreater(len(payload["results"]), 0)
            self.assertEqual(payload["results"][0]["result"]["path"], "knowledge/horas-in-itinere.md")
            diagnostics = payload["query_diagnostics"]
            self.assertEqual(diagnostics["strict_query"], '"deslocamento" "casa" "trabalho" "conta" "como" "jornada"')
            self.assertEqual(diagnostics["relaxed_query"], '"deslocamento" AND "casa" AND "trabalho" AND "como" AND "jornada"')
            self.assertTrue(diagnostics["relaxation_applied"])

    def test_bm25_search_uses_lower_signal_mass_for_natural_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="custom")
            write_concept(
                root,
                "antibiotico-extracao.md",
                (
                    "type: Reference",
                    "title: Antibiotico apos extracao",
                    "description: Receita para controle de infeccao apos extracao.",
                    "tags: [clinica]",
                    "timestamp: 2026-06-22T00:00:00Z",
                ),
                "# Context\n\nTomar antibiotico apos extracao quando houver sinal de infeccao.\n",
            )
            write_concept(
                root,
                "bruxismo-dente.md",
                (
                    "type: Reference",
                    "title: Bruxismo e desgaste no dente",
                    "description: Sinais de desgaste no dente.",
                    "tags: [clinica]",
                    "timestamp: 2026-06-22T00:00:00Z",
                ),
                "# Context\n\nDente com desgaste pode indicar bruxismo noturno.\n",
            )
            write_concept(
                root,
                "limpeza-tempo.md",
                (
                    "type: Reference",
                    "title: Tempo de limpeza profissional",
                    "description: Duracao de limpeza profissional.",
                    "tags: [clinica]",
                    "timestamp: 2026-06-22T00:00:00Z",
                ),
                "# Context\n\nTempo medio de limpeza profissional e de quarenta minutos.\n",
            )
            rebuild_index(root)

            result = run_cairn(
                root,
                "search",
                "Preciso tomar antibiotico apos extracao de dente. O que devo tomar e por quanto tempo?",
                "--json",
                "--explain",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertGreater(len(payload["results"]), 0)
            self.assertEqual(payload["results"][0]["result"]["path"], "knowledge/antibiotico-extracao.md")
            diagnostics = payload["query_diagnostics"]
            self.assertEqual(diagnostics["relaxed_query"], '"tomar" AND "antibiotico" AND "apos" AND "extracao"')
            self.assertTrue(diagnostics["relaxation_applied"])

    def test_cli_search_json_explain_does_not_report_stopword_relaxation(self) -> None:
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
            rebuild_index(root)

            result = run_cairn(root, "search", "yoga breathing exercises for beginners", "--json", "--explain")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            diagnostics = payload["query_diagnostics"]
            self.assertEqual(diagnostics["zero_hit_terms"], ["yoga", "breathing", "exercises", "beginners"])
            self.assertEqual(diagnostics["relaxed_query"], "")
            self.assertFalse(diagnostics["relaxation_applied"])
            self.assertEqual(payload["results"], [])

    def test_rrf_search_recovers_safe_inflection_variant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "token-rotation.md",
                (
                    "type: Runbook",
                    "title: Token rotation",
                    "description: Procedure for CI token rotation.",
                    "tags: [deploy, security]",
                    "timestamp: 2026-06-17T10:00:00Z",
                    "signals: [token rotation]",
                ),
                "# Resolution\n\nUse the token rotation procedure and update the CI secret.\n",
            )
            rebuild_index(root)

            default_results = search(root, "rotating", limit=3)
            fused_results = search(root, "rotating", limit=3, ranker="rrf")

            self.assertEqual(default_results, [])
            self.assertEqual(fused_results[0].path, "knowledge/token-rotation.md")

    def test_metadata_only_match_returns_metadata_snippet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "metadata.md",
                (
                    "type: Runbook",
                    "title: Metadata only",
                    "description: Mentions ultraunique-signal only in metadata.",
                    "tags: [deploy]",
                    "timestamp: 2026-06-17T10:00:00Z",
                    "signals: [ultraunique-signal]",
                ),
                "# Context\n\nNo matching body words here.\n",
            )
            rebuild_index(root)

            results = search(root, "ultraunique-signal", limit=3)

            self.assertEqual(len(results), 1)
            self.assertIn("ultraunique", results[0].snippet)

    def test_search_passages_returns_heading_and_line_range(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "deploy-403.md",
                (
                    "type: Runbook",
                    "title: Deploy 403",
                    "description: Fix deploy failures.",
                    "tags: [deploy, bug]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nNoise.\n\n# Resolution\n\nRotate the CI token.\n",
            )
            rebuild_index(root)

            from cairn.indexer import search_passages

            results = search_passages(root, "rotate ci token", limit=3)

            self.assertEqual(results[0].path, "knowledge/deploy-403.md")
            self.assertEqual(results[0].heading, "Resolution")
            self.assertGreater(results[0].end_line, results[0].start_line)
            self.assertIn("token", results[0].snippet.casefold())

    def test_rrf_search_passages_recovers_safe_inflection_variant(self) -> None:
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
            rebuild_index(root)

            from cairn.indexer import search_passages

            default_results = search_passages(root, "reconnecting", limit=3)
            fused_results = search_passages(root, "reconnecting", limit=3, ranker="rrf")

            self.assertEqual(default_results, [])
            self.assertEqual(fused_results[0].path, "knowledge/cache-failover.md")
            self.assertEqual(fused_results[0].heading, "Resolution")
            self.assertIn("reconnection", fused_results[0].text)

    def test_config_excluded_folders_are_not_indexed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            (root / "inbox" / "draft.md").write_text(
                "---\n"
                "type: Note\n"
                "title: Draft excluded\n"
                "description: secretneedle should not be indexed.\n"
                "tags: [personal]\n"
                "timestamp: 2026-06-17T10:00:00Z\n"
                "---\n\n"
                "# Context\n\nsecretneedle appears in excluded inbox.\n",
                encoding="utf-8",
            )
            rebuild_index(root)

            results = search(root, "secretneedle", limit=3)

            self.assertEqual(results, [])

    def test_literal_brackets_in_metadata_do_not_hide_body_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "brackets.md",
                (
                    "type: Runbook",
                    "title: [Decorated] title",
                    "description: Bracketed metadata.",
                    "tags: [deploy]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nThe body has a needleword match.\n",
            )
            rebuild_index(root)

            results = search(root, "needleword", limit=3)

            self.assertEqual(len(results), 1)
            self.assertIn("[needleword]", results[0].snippet)

    def test_missing_index_error_is_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")

            with self.assertRaisesRegex(Exception, "apollokairn index|rebuild"):
                search(root, "anything", limit=3)

    def test_search_incomplete_index_schema_raises_index_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_concept(
                root,
                "note.md",
                (
                    "type: Note",
                    "title: Needle",
                    "description: schemaneedle.",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
            )
            rebuild_index(root)
            con = sqlite3.connect(root / ".cairn" / "index.db")
            try:
                con.execute("DROP TABLE index_meta")
                con.commit()
            finally:
                con.close()

            with self.assertRaises(CairnIndexError):
                search(root, "schemaneedle", limit=3)

    def test_search_passages_incomplete_index_schema_raises_index_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_concept(
                root,
                "note.md",
                (
                    "type: Note",
                    "title: Needle",
                    "description: schemaneedle.",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nschemapassage.\n",
            )
            rebuild_index(root)
            con = sqlite3.connect(root / ".cairn" / "index.db")
            try:
                con.execute("DROP TABLE index_meta")
                con.commit()
            finally:
                con.close()

            with self.assertRaises(CairnIndexError):
                search_passages(root, "schemapassage", limit=3)

    def test_index_path_directory_raises_index_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            (root / ".cairn" / "index.db").mkdir()

            with self.assertRaises(CairnIndexError):
                search(root, "anything", limit=3)

    def test_rebuild_index_path_directory_raises_index_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            (root / ".cairn" / "index.db").mkdir()

            with self.assertRaises(CairnIndexError):
                rebuild_index(root)

    def test_rebuild_corrupt_index_file_raises_index_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            (root / ".cairn" / "index.db").write_bytes(b"not a sqlite database")

            with self.assertRaises(CairnIndexError):
                rebuild_index(root)

    def test_cli_search_index_path_directory_returns_concise_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            (root / ".cairn" / "index.db").mkdir()

            result = run_cairn(root, "search", "anything")

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertIn("apollokairn index --rebuild", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_cli_index_path_directory_returns_concise_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            (root / ".cairn" / "index.db").mkdir()

            result = run_cairn(root, "index", "--rebuild")

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertIn("apollokairn index --rebuild", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_cli_index_corrupt_index_file_returns_concise_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            (root / ".cairn" / "index.db").write_bytes(b"not a sqlite database")

            result = run_cairn(root, "index", "--rebuild")

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertIn("apollokairn index --rebuild", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_cli_index_path_rebuilds_vault_from_outside_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "vault"
            outside = base / "outside"
            outside.mkdir()
            init_vault(root, profile_name="personal")

            result = run_cairn(outside, "index", "--path", str(root), "--rebuild")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / ".cairn" / "index.db").is_file())
            self.assertIn(str(root / ".cairn" / "index.db"), result.stdout)

    def test_cli_index_json_returns_incremental_stats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_concept(
                root,
                "note.md",
                (
                    "type: Note",
                    "title: Note",
                    "description: A note.",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nBody.\n",
            )

            result = run_cairn(root, "index", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"])
            self.assertFalse(payload["rebuild"])
            self.assertEqual(payload["updated"], 1)
            self.assertEqual(payload["removed"], 0)
            self.assertEqual(payload["skipped"], 0)
            self.assertTrue(payload["index_path"].endswith(".cairn/index.db") or payload["index_path"].endswith(".cairn\\index.db"))

    def test_cli_index_without_rebuild_updates_changed_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            concept = write_concept(
                root,
                "note.md",
                (
                    "type: Note",
                    "title: Old needle",
                    "description: oldneedle description.",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\noldneedle body.\n",
            )
            run_cairn(root, "index", "--rebuild")
            concept.write_text(
                "---\n"
                "type: Note\n"
                "title: New needle\n"
                "description: newneedle description.\n"
                "tags: [personal]\n"
                "timestamp: 2026-06-17T10:00:00Z\n"
                "---\n\n"
                "# Context\n\nnewneedle body.\n",
                encoding="utf-8",
            )

            result = run_cairn(root, "index")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("updated 1", result.stdout)
            self.assertEqual(search(root, "oldneedle", limit=3), [])
            self.assertEqual(search(root, "newneedle", limit=3)[0].path, "knowledge/note.md")

    def test_cli_index_without_rebuild_removes_deleted_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            concept = write_concept(
                root,
                "gone.md",
                (
                    "type: Note",
                    "title: Gone needle",
                    "description: goneneedle description.",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\ngoneneedle body.\n",
            )
            run_cairn(root, "index", "--rebuild")
            concept.unlink()

            result = run_cairn(root, "index")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("removed 1", result.stdout)
            self.assertEqual(search(root, "goneneedle", limit=3), [])

    def test_search_repairs_changed_document_before_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            concept = write_concept(
                root,
                "note.md",
                (
                    "type: Note",
                    "title: Old needle",
                    "description: oldneedle description.",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\noldneedle body.\n",
            )
            rebuild_index(root)
            concept.write_text(
                "---\n"
                "type: Note\n"
                "title: New needle\n"
                "description: newneedle description.\n"
                "tags: [personal]\n"
                "timestamp: 2026-06-17T10:00:00Z\n"
                "---\n\n"
                "# Context\n\nnewneedle body.\n",
                encoding="utf-8",
            )

            results = search(root, "newneedle", limit=3)

            self.assertEqual([result.path for result in results], ["knowledge/note.md"])
            self.assertEqual(search(root, "oldneedle", limit=3), [])

    def test_search_repairs_changed_document_with_same_mtime_and_size(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            concept = write_concept(
                root,
                "note.md",
                (
                    "type: Note",
                    "title: Oldneedle",
                    "description: oldneedle.",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\noldneedle.\n",
            )
            rebuild_index(root)
            original_stat = concept.stat()
            old_text = concept.read_text(encoding="utf-8")
            new_text = old_text.replace("Oldneedle", "Newneedle").replace("oldneedle", "newneedle")
            concept.write_text(new_text, encoding="utf-8")
            self.assertEqual(concept.stat().st_size, original_stat.st_size)
            os.utime(concept, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))

            results = search(root, "newneedle", limit=3)

            self.assertEqual([result.path for result in results], ["knowledge/note.md"])
            self.assertEqual(search(root, "oldneedle", limit=3), [])

    def test_search_repairs_new_document_before_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_concept(
                root,
                "indexed.md",
                (
                    "type: Note",
                    "title: Indexed",
                    "description: indexedneedle description.",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
            )
            rebuild_index(root)
            write_concept(
                root,
                "new.md",
                (
                    "type: Note",
                    "title: New",
                    "description: freshneedle description.",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nfreshneedle body.\n",
            )

            results = search(root, "freshneedle", limit=3)

            self.assertEqual([result.path for result in results], ["knowledge/new.md"])

    def test_search_repairs_removed_document_before_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            concept = write_concept(
                root,
                "gone.md",
                (
                    "type: Note",
                    "title: Gone",
                    "description: goneneedle description.",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\ngoneneedle body.\n",
            )
            rebuild_index(root)
            concept.unlink()

            results = search(root, "goneneedle", limit=3)

            self.assertEqual(results, [])

    def test_search_passages_repairs_changed_document_before_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            concept = write_concept(
                root,
                "deploy.md",
                (
                    "type: Runbook",
                    "title: Deploy",
                    "description: Old deploy note.",
                    "tags: [deploy]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Resolution\n\noldpassage only.\n",
            )
            rebuild_index(root)
            concept.write_text(
                "---\n"
                "type: Runbook\n"
                "title: Deploy\n"
                "description: New deploy note.\n"
                "tags: [deploy]\n"
                "timestamp: 2026-06-17T10:00:00Z\n"
                "---\n\n"
                "# Resolution\n\nnewpassage only.\n",
                encoding="utf-8",
            )

            results = search_passages(root, "newpassage", limit=3)

            self.assertEqual([result.path for result in results], ["knowledge/deploy.md"])
            self.assertIn("newpassage", results[0].text)

    def test_search_passages_repairs_changed_document_with_same_mtime_and_size(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            concept = write_concept(
                root,
                "deploy.md",
                (
                    "type: Runbook",
                    "title: Deploy",
                    "description: Old deploy note.",
                    "tags: [deploy]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Resolution\n\noldpassage only.\n",
            )
            rebuild_index(root)
            original_stat = concept.stat()
            old_text = concept.read_text(encoding="utf-8")
            new_text = old_text.replace("Old deploy", "New deploy").replace("oldpassage", "newpassage")
            concept.write_text(new_text, encoding="utf-8")
            self.assertEqual(concept.stat().st_size, original_stat.st_size)
            os.utime(concept, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))

            results = search_passages(root, "newpassage", limit=3)

            self.assertEqual([result.path for result in results], ["knowledge/deploy.md"])
            self.assertIn("newpassage", results[0].text)
            self.assertEqual(search_passages(root, "oldpassage", limit=3), [])

    def test_cli_search_missing_index_returns_concise_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")

            result = run_cairn(root, "search", "anything")

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertIn("apollokairn index --rebuild", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_cli_search_json_returns_metadata_without_full_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "json.md",
                (
                    "type: Runbook",
                    "title: JSON searchable",
                    "description: Metadata jsonneedle.",
                    "tags: [deploy]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nFULL_BODY_SHOULD_NOT_APPEAR in the complete document.\n",
            )
            rebuild_index(root)

            result = run_cairn(root, "search", "jsonneedle", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload[0]["path"], "knowledge/json.md")
            self.assertIn("snippet", payload[0])
            self.assertNotIn("body", payload[0])
            self.assertNotIn("FULL_BODY_SHOULD_NOT_APPEAR", result.stdout)

    def test_cli_search_json_explain_reports_matched_fields_without_confidence_claims(self) -> None:
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
            rebuild_index(root)

            result = run_cairn(root, "search", "deploy 403 token", "--json", "--explain")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["query"], "deploy 403 token")
            diagnostics = payload["query_diagnostics"]
            self.assertEqual(diagnostics["strict_query"], '"deploy" "403" "token"')
            self.assertEqual(diagnostics["zero_hit_terms"], [])
            self.assertEqual(diagnostics["relaxed_query"], "")
            self.assertFalse(diagnostics["relaxation_applied"])
            first = payload["results"][0]
            self.assertEqual(first["result"]["path"], "knowledge/deploy-403.md")
            explanation = first["explanation"]
            self.assertEqual(explanation["path"], "knowledge/deploy-403.md")
            self.assertIn("not confidence", explanation["score_note"])
            matched = {item["term"]: item["fields"] for item in explanation["matched_terms"]}
            self.assertIn("title", matched["deploy"])
            self.assertIn("signals", matched["token"])

    def test_cli_search_json_explain_reports_zero_hit_relaxation(self) -> None:
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
            rebuild_index(root)

            result = run_cairn(root, "search", "credentials xyzzy", "--json", "--explain")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            diagnostics = payload["query_diagnostics"]
            self.assertEqual(diagnostics["strict_query"], '"credentials" "xyzzy"')
            self.assertEqual(diagnostics["zero_hit_terms"], ["xyzzy"])
            self.assertEqual(diagnostics["relaxed_query"], '"credentials"')
            self.assertTrue(diagnostics["relaxation_applied"])
            self.assertEqual(payload["results"][0]["result"]["path"], "knowledge/deploy-credentials.md")

    def test_cli_search_path_searches_vault_from_outside_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "vault"
            outside = base / "outside"
            outside.mkdir()
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "deploy-403.md",
                (
                    "type: Runbook",
                    "title: Fix deploy 403",
                    "description: Permission failure.",
                    "tags: [deploy, bug]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nDeploy fails with HTTP 403 during release.\n",
            )
            rebuild_index(root)

            result = run_cairn(outside, "search", "deploy 403", "--path", str(root))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("knowledge/deploy-403.md", result.stdout)

    def test_cli_search_accepts_rrf_ranker(self) -> None:
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
                "search",
                "deploy token rotation kubernetes secret",
                "--ranker",
                "rrf",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("knowledge/deploy-secret.md", result.stdout)

    def test_cli_search_type_filter_excludes_other_matching_types(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "vault"
            outside = base / "outside"
            outside.mkdir()
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "runbook.md",
                (
                    "type: Runbook",
                    "title: Shared needle runbook",
                    "description: Mentions sharedneedle.",
                    "tags: [bug]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nsharedneedle appears here.\n",
            )
            write_concept(
                root,
                "decision.md",
                (
                    "type: Decision",
                    "title: Shared needle decision",
                    "description: Mentions sharedneedle.",
                    "tags: [architecture]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nsharedneedle appears here too.\n",
            )
            rebuild_index(root)

            result = run_cairn(
                outside,
                "search",
                "sharedneedle",
                "--path",
                str(root),
                "--type",
                "Decision",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("knowledge/decision.md", result.stdout)
            self.assertNotIn("knowledge/runbook.md", result.stdout)

    def test_cli_search_tag_filter_excludes_other_matching_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "vault"
            outside = base / "outside"
            outside.mkdir()
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "deploy.md",
                (
                    "type: Runbook",
                    "title: Shared tag deploy",
                    "description: Mentions tagneedle.",
                    "tags: [deploy]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\ntagneedle appears here.\n",
            )
            write_concept(
                root,
                "architecture.md",
                (
                    "type: Decision",
                    "title: Shared tag architecture",
                    "description: Mentions tagneedle.",
                    "tags: [architecture]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\ntagneedle appears here too.\n",
            )
            rebuild_index(root)

            result = run_cairn(
                outside,
                "search",
                "tagneedle",
                "--path",
                str(root),
                "--tag",
                "architecture",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("knowledge/architecture.md", result.stdout)
            self.assertNotIn("knowledge/deploy.md", result.stdout)

    def test_cli_search_system_filter_excludes_other_matching_systems(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "vault"
            outside = base / "outside"
            outside.mkdir()
            init_vault(root, profile_name="engineering")
            write_concept(
                root,
                "ci.md",
                (
                    "type: Runbook",
                    "title: Shared system ci",
                    "description: Mentions systemneedle.",
                    "tags: [deploy]",
                    "timestamp: 2026-06-17T10:00:00Z",
                    "systems: [ci]",
                ),
                "# Context\n\nsystemneedle appears here.\n",
            )
            write_concept(
                root,
                "payments.md",
                (
                    "type: Runbook",
                    "title: Shared system payments",
                    "description: Mentions systemneedle.",
                    "tags: [bug]",
                    "timestamp: 2026-06-17T10:00:00Z",
                    "systems: [payments]",
                ),
                "# Context\n\nsystemneedle appears here too.\n",
            )
            rebuild_index(root)

            result = run_cairn(
                outside,
                "search",
                "systemneedle",
                "--path",
                str(root),
                "--system",
                "payments",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("knowledge/payments.md", result.stdout)
            self.assertNotIn("knowledge/ci.md", result.stdout)

    def test_cli_search_rejects_negative_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")

            result = run_cairn(root, "search", "anything", "--limit", "-1")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--limit must be positive", result.stderr)

    def test_show_returns_full_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_concept(
                root,
                "note.md",
                (
                    "type: Note",
                    "title: Note",
                    "description: A note.",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nFull body.\n",
            )

            text = show(root, "knowledge/note.md")

            self.assertIn("type: Note", text)
            self.assertIn("Full body.", text)

    def test_show_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")

            with self.assertRaises(ValueError):
                show(root, "../outside.md")

    def test_cli_show_missing_file_returns_concise_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")

            result = run_cairn(root, "show", "missing.md")

            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("ERROR", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_cli_show_path_traversal_returns_concise_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")

            result = run_cairn(root, "show", "../outside.md")

            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("ERROR", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_cli_show_path_reads_vault_document_from_outside_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "vault"
            outside = base / "outside"
            outside.mkdir()
            init_vault(root, profile_name="personal")
            write_concept(
                root,
                "note.md",
                (
                    "type: Note",
                    "title: Note",
                    "description: A note.",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nFull body.\n",
            )

            result = run_cairn(outside, "show", "knowledge/note.md", "--path", str(root))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Full body.", result.stdout)

    def test_cli_show_lines_returns_only_requested_line_range(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_concept(
                root,
                "note.md",
                (
                    "type: Note",
                    "title: Note",
                    "description: A note.",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "line one\nline two\nline three\n",
            )

            result = run_cairn(root, "show", "knowledge/note.md", "--lines", "9:10")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "line one\nline two\n")

    def test_cli_show_section_returns_only_named_markdown_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_concept(
                root,
                "note.md",
                (
                    "type: Note",
                    "title: Note",
                    "description: A note.",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nIgnore this.\n\n# Diagnosis\n\nKeep this.\n\n# Resolution\n\nIgnore that.\n",
            )

            result = run_cairn(root, "show", "knowledge/note.md", "--section", "Diagnosis")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("# Diagnosis", result.stdout)
            self.assertIn("Keep this.", result.stdout)
            self.assertNotIn("Ignore this.", result.stdout)
            self.assertNotIn("Ignore that.", result.stdout)

    def test_cli_show_section_matches_heading_without_accents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="support")
            write_concept(
                root,
                "atendimento.md",
                (
                    "type: Procedure",
                    "title: Atendimento",
                    "description: A note.",
                    "tags: [suporte]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Contexto\n\nIgnore.\n\n# Solução\n\nManter este trecho.\n\n# Pós-validação\n\nIgnore.\n",
            )

            result = run_cairn(root, "show", "knowledge/atendimento.md", "--section", "Solucao")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("# Solução", result.stdout)
            self.assertIn("Manter este trecho.", result.stdout)
            self.assertNotIn("Ignore.", result.stdout)

    def test_cli_show_snippet_returns_nearby_matching_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_concept(
                root,
                "note.md",
                (
                    "type: Note",
                    "title: Note",
                    "description: A note.",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "alpha\nbefore\nneedle target\nafter\nomega\n",
            )

            result = run_cairn(root, "show", "knowledge/note.md", "--snippet", "needle", "--context", "1")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("before", result.stdout)
            self.assertIn("needle target", result.stdout)
            self.assertIn("after", result.stdout)
            self.assertNotIn("alpha", result.stdout)
            self.assertNotIn("omega", result.stdout)

    def test_cli_show_json_returns_selected_content_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            write_concept(
                root,
                "note.md",
                (
                    "type: Note",
                    "title: Note",
                    "description: A note.",
                    "tags: [personal]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "# Context\n\nIgnore this.\n\n# Resolution\n\nKeep this.\n",
            )

            result = run_cairn(root, "show", "knowledge/note.md", "--section", "Resolution", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["path"], "knowledge/note.md")
            self.assertEqual(payload["mode"], "section")
            self.assertEqual(payload["selector"], "Resolution")
            self.assertGreater(payload["tokens"], 0)
            self.assertIn("# Resolution", payload["content"])
            self.assertNotIn("Ignore this.", payload["content"])

    def test_cli_show_snippet_matches_text_without_accents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="support")
            write_concept(
                root,
                "sessao.md",
                (
                    "type: Procedure",
                    "title: Sessão",
                    "description: A note.",
                    "tags: [suporte]",
                    "timestamp: 2026-06-17T10:00:00Z",
                ),
                "antes\nrenovação de sessão concluída\ndepois\n",
            )

            result = run_cairn(root, "show", "knowledge/sessao.md", "--snippet", "renovacao sessao", "--context", "0")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "renovação de sessão concluída\n")


if __name__ == "__main__":
    unittest.main()
