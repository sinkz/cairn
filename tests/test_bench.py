from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_bench(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env.setdefault("APOLLOKAIRN_REGISTRY_PATH", str(ROOT / ".cairn" / f"test-registry-{os.getpid()}.json"))
    return subprocess.run(
        [sys.executable, "bench/run_eval.py", *args],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def run_writeback_bench(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env.setdefault("APOLLOKAIRN_REGISTRY_PATH", str(ROOT / ".cairn" / f"test-registry-{os.getpid()}.json"))
    return subprocess.run(
        [sys.executable, "bench/run_writeback_eval.py", *args],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write_doc(root: Path, rel: str, title: str, systems: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        "type: Runbook\n"
        f"title: {title}\n"
        "description: Shared deploy diagnostic.\n"
        "tags: [deploy]\n"
        "timestamp: 2026-06-17T10:00:00Z\n"
        f"systems: [{systems}]\n"
        "---\n\n"
        "# Context\n\nshared deploy needle\n",
        encoding="utf-8",
    )


class BenchTests(unittest.TestCase):
    def test_public_benchmark_data_exposes_retrieval_and_writeback_suites(self) -> None:
        data = json.loads((ROOT / "docs" / "data" / "benchmarks.json").read_text(encoding="utf-8"))

        suites = {suite["id"]: suite for suite in data["suites"]}
        self.assertIn("retrieval", suites)
        self.assertIn("writeback", suites)
        self.assertEqual(
            suites["writeback"]["suite"]["command"],
            "python bench/run_writeback_eval.py --quiet --compare-golden bench/writeback/golden.json",
        )
        writeback_metric_ids = {metric["id"] for metric in suites["writeback"]["current"]["metrics"]}
        self.assertTrue(
            {
                "decision_accuracy",
                "target_path_accuracy",
                "noop_accuracy",
                "conflict_detection_rate",
                "duplicate_avoidance_rate",
                "writeback_cases",
            }.issubset(writeback_metric_ids),
            writeback_metric_ids,
        )
        self.assertGreaterEqual(len(suites["writeback"]["history"]), 1)
        self.assertIn("decision_accuracy", suites["writeback"]["history"][0])

    def test_public_writeback_metrics_match_current_benchmark_output(self) -> None:
        result = run_writeback_bench()

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        data = json.loads((ROOT / "docs" / "data" / "benchmarks.json").read_text(encoding="utf-8"))
        writeback = next(suite for suite in data["suites"] if suite["id"] == "writeback")
        public_metrics = {metric["id"]: metric["value"] for metric in writeback["current"]["metrics"]}

        self.assertEqual(public_metrics["decision_accuracy"], payload["decision_accuracy"])
        self.assertEqual(public_metrics["target_path_accuracy"], payload["target_path_accuracy"])
        self.assertEqual(public_metrics["noop_accuracy"], payload["noop_accuracy"])
        self.assertEqual(public_metrics["conflict_detection_rate"], payload["conflict_detection_rate"])
        self.assertEqual(public_metrics["duplicate_avoidance_rate"], payload["duplicate_avoidance_rate"])
        self.assertEqual(public_metrics["writeback_cases"], payload["cases"])

    def test_public_retrieval_metrics_match_current_benchmark_output(self) -> None:
        result = run_bench()

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        data = json.loads((ROOT / "docs" / "data" / "benchmarks.json").read_text(encoding="utf-8"))
        retrieval = next(suite for suite in data["suites"] if suite["id"] == "retrieval")
        public_metrics = {metric["id"]: metric["value"] for metric in retrieval["current"]["metrics"]}

        self.assertEqual(public_metrics["recall_at_3"], payload["mean_recall_at_k"])
        self.assertEqual(public_metrics["mrr_at_3"], payload["mean_mrr_at_k"])
        self.assertEqual(public_metrics["ndcg_at_3"], payload["mean_ndcg_at_k"])
        self.assertEqual(public_metrics["context_reduction"], payload["context_reduction"])
        self.assertEqual(public_metrics["comparison_reduction"], payload["comparison"]["token_reduction"])
        self.assertEqual(retrieval["current"]["corpus"], payload["corpus"])
        self.assertEqual(retrieval["current"]["slice_metrics"], payload["slice_metrics"])
        self.assertEqual(retrieval["current"]["quality"], payload["quality"])
        self.assertEqual(retrieval["current"]["efficiency"], payload["efficiency"])
        self.assertEqual(data["current"]["corpus"], payload["corpus"])
        self.assertEqual(data["current"]["slice_metrics"], payload["slice_metrics"])
        self.assertEqual(data["current"]["quality"], payload["quality"])
        self.assertEqual(data["current"]["efficiency"], payload["efficiency"])

    def test_benchmark_outputs_quality_and_token_metrics_for_harder_suite(self) -> None:
        result = run_bench()

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("mean_recall_at_k", payload)
        self.assertIn("mean_mrr_at_k", payload)
        self.assertIn("mean_ndcg_at_k", payload)
        self.assertIn("returned_tokens", payload)
        self.assertIn("context_reduction", payload)
        self.assertEqual(payload["quality"]["mean_recall_at_k"], payload["mean_recall_at_k"])
        self.assertEqual(payload["quality"]["mean_mrr_at_k"], payload["mean_mrr_at_k"])
        self.assertEqual(payload["quality"]["mean_ndcg_at_k"], payload["mean_ndcg_at_k"])
        self.assertEqual(payload["efficiency"]["returned_tokens"], payload["returned_tokens"])
        self.assertEqual(payload["efficiency"]["context_reduction"], payload["context_reduction"])
        self.assertEqual(payload["efficiency"]["budget_compliance_rate"], 1.0)
        self.assertIn("slice_metrics", payload)
        self.assertGreaterEqual(payload["topics"], 10)
        metrics_by_slice = {item["slice"]: item for item in payload["slice_metrics"]}
        self.assertEqual(
            metrics_by_slice["role_workflow"]["topics"],
            payload["corpus"]["topics_by_slice"]["role_workflow"],
        )
        self.assertEqual(metrics_by_slice["passage_budget"]["topics"], 5)
        self.assertEqual(metrics_by_slice["passage_budget"]["budget_compliance_rate"], 1.0)
        self.assertTrue(any(item["mode"] == "passages" for item in payload["per_topic"]))
        passage_topic = next(item for item in payload["per_topic"] if item["mode"] == "passages")
        self.assertEqual(passage_topic["compare"]["mode"], "documents")
        self.assertGreater(passage_topic["compare"]["returned_tokens"], passage_topic["returned_tokens"])
        self.assertGreaterEqual(passage_topic["compare"]["token_reduction"], 0.2)
        compare_topics = [
            item
            for item in payload["per_topic"]
            if "compare" in item and item["compare"]["returned_tokens"] > item["returned_tokens"]
        ]
        comparison = payload["comparison"]
        self.assertGreaterEqual(comparison["topics"], 4)
        self.assertEqual(comparison["topics"], len(compare_topics))
        self.assertEqual(comparison["candidate_tokens"], sum(item["returned_tokens"] for item in compare_topics))
        self.assertEqual(
            comparison["baseline_tokens"],
            sum(item["compare"]["returned_tokens"] for item in compare_topics),
        )
        self.assertGreaterEqual(comparison["token_reduction"], 0.4)
        rrf_topic = next(item for item in payload["per_topic"] if item.get("ranker") == "rrf")
        self.assertEqual(rrf_topic["docs"][0], "knowledge/deploy-403.md")
        self.assertEqual(rrf_topic["recall_at_k"], 1.0)
        self.assertEqual(rrf_topic["compare"]["ranker"], "bm25")
        self.assertEqual(rrf_topic["compare"]["recall_at_k"], 0.0)

    def test_benchmark_reports_corpus_metadata(self) -> None:
        result = run_bench()

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        corpus = payload["corpus"]
        self.assertEqual(corpus["markdown_files"], 25)
        self.assertEqual(corpus["topics"], 28)
        self.assertEqual(corpus["qrel_rows"], 31)
        self.assertEqual(corpus["positive_qrels"], 31)
        self.assertEqual(corpus["answerable_topics"], 28)
        self.assertEqual(corpus["no_answer_topics"], 0)
        self.assertEqual(corpus["mean_positive_qrels_per_answerable_topic"], 1.1071)
        self.assertIn("role_workflow", corpus["slices"])
        self.assertEqual(corpus["topics_by_slice"]["passage_budget"], 5)

    def test_benchmark_metadata_allows_no_answer_topics_without_qrels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            topics = base / "topics.jsonl"
            topics.write_text(
                '{"id":"q_no_answer","query":"constellation payroll zephyr banana","category":"no_answer","budget":400}\n',
                encoding="utf-8",
            )
            qrels = base / "qrels.tsv"
            qrels.write_text("", encoding="utf-8")

            result = run_bench(
                "--topics",
                str(topics),
                "--qrels",
                str(qrels),
                "--min-mrr",
                "0",
                "--min-ndcg",
                "0",
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        corpus = json.loads(result.stdout)["corpus"]
        self.assertEqual(corpus["topics"], 1)
        self.assertEqual(corpus["answerable_topics"], 0)
        self.assertEqual(corpus["no_answer_topics"], 1)
        self.assertEqual(corpus["qrel_rows"], 0)
        slice_metrics = json.loads(result.stdout)["slice_metrics"]
        self.assertEqual(slice_metrics[0]["slice"], "no_answer")
        self.assertEqual(slice_metrics[0]["false_positive_rate"], 0.0)

    def test_benchmark_tracks_required_quality_categories(self) -> None:
        result = run_bench()

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        categories = {item.get("category") for item in payload["per_topic"]}
        self.assertNotIn(None, categories)
        self.assertTrue(
            {
                "exact_error",
                "filters",
                "passage_budget",
                "rrf_extra_terms",
                "rrf_inflection",
                "rrf_passage",
                "alias",
                "multilingual",
                "rrf_filter",
                "role_workflow",
                "access",
                "library",
                "vocabulary",
                "same_problem_synonyms",
                "support_access_synonyms",
                "tooling_abbreviation",
            }.issubset(categories),
            categories,
        )

    def test_benchmark_includes_synonym_stress_cases(self) -> None:
        result = run_bench()

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        topics = {item["id"]: item for item in payload["per_topic"]}

        self.assertEqual(topics["q26"]["category"], "same_problem_synonyms")
        self.assertEqual(topics["q26"]["docs"][0], "knowledge/k8s-rollback.md")
        self.assertEqual(topics["q26"]["recall_at_k"], 1.0)

        self.assertEqual(topics["q27"]["category"], "support_access_synonyms")
        self.assertEqual(topics["q27"]["docs"][0], "processes/production-access-request.md")

        self.assertEqual(topics["q28"]["category"], "tooling_abbreviation")
        self.assertEqual(topics["q28"]["docs"][0], "decisions/use-ruff-formatting.md")

    def test_benchmark_has_vocabulary_slice_for_glossary_aliases(self) -> None:
        result = run_bench()

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        topic = next(item for item in payload["per_topic"] if item["id"] == "q25")
        self.assertEqual(topic["category"], "vocabulary")
        self.assertEqual(topic["ranker"], "bm25")
        self.assertEqual(topic["docs"][0], "knowledge/k8s-rollback.md")
        self.assertEqual(topic["recall_at_k"], 1.0)

    def test_benchmark_applies_topic_filters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            fixture = base / "vault"
            fixture.mkdir()
            (fixture / "SCHEMA.md").write_text(
                "# ApolloKairn Schema\n\n"
                "## Types\n\n"
                "- Runbook\n\n"
                "## Tags\n\n"
                "- deploy\n",
                encoding="utf-8",
            )
            write_doc(fixture, "knowledge/ci-deploy.md", "CI deploy", "ci")
            write_doc(fixture, "knowledge/mobile-deploy.md", "Mobile deploy", "mobile")
            topics = base / "topics.jsonl"
            topics.write_text(
                '{"id":"q_filter","query":"shared deploy needle","system":["mobile"],"budget":400}\n',
                encoding="utf-8",
            )
            qrels = base / "qrels.tsv"
            qrels.write_text("q_filter\tknowledge/mobile-deploy.md\t3\n", encoding="utf-8")

            result = run_bench("--fixture", str(fixture), "--topics", str(topics), "--qrels", str(qrels))

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["per_topic"][0]["docs"], ["knowledge/mobile-deploy.md"])
            self.assertEqual(payload["per_topic"][0]["filters"], {"system": ["mobile"]})

    def test_passage_benchmark_counts_unique_documents_for_doc_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            topics = base / "topics.jsonl"
            topics.write_text(
                '{"id":"q_passage","query":"jwt expired clock skew auth","mode":"passages","budget":400}\n',
                encoding="utf-8",
            )
            qrels = base / "qrels.tsv"
            qrels.write_text("q_passage\tknowledge/jwt-clock-skew.md\t3\n", encoding="utf-8")

            result = run_bench("--topics", str(topics), "--qrels", str(qrels))

            self.assertEqual(result.returncode, 0, result.stderr)
            topic = json.loads(result.stdout)["per_topic"][0]
            self.assertEqual(topic["docs"], ["knowledge/jwt-clock-skew.md"])
            self.assertLessEqual(topic["recall_at_k"], 1.0)
            self.assertLessEqual(topic["ndcg_at_k"], 1.0)

    def test_benchmark_compare_golden_detects_ranking_regression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            golden = Path(tmp) / "golden.json"
            golden.write_text('{"q1":["wrong.md"]}\n', encoding="utf-8")

            result = run_bench("--compare-golden", str(golden))

            self.assertEqual(result.returncode, 1)
            self.assertIn("golden regression", result.stderr)

    def test_benchmark_compare_golden_detects_topic_set_regression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            golden = Path(tmp) / "golden.json"
            golden.write_text('{"q1":["knowledge/deploy-403.md"]}\n', encoding="utf-8")

            result = run_bench("--compare-golden", str(golden))

            self.assertEqual(result.returncode, 1)
            self.assertIn("missing from golden", result.stderr)

    def test_benchmark_rejects_duplicate_topic_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            topics = base / "topics.jsonl"
            topics.write_text(
                '{"id":"q_dup","query":"deploy 403 token rotation","budget":400}\n'
                '{"id":"q_dup","query":"jwt expired clock skew auth","budget":400}\n',
                encoding="utf-8",
            )
            qrels = base / "qrels.tsv"
            qrels.write_text("q_dup\tknowledge/deploy-403.md\t3\n", encoding="utf-8")

            result = run_bench("--topics", str(topics), "--qrels", str(qrels))

        self.assertEqual(result.returncode, 2)
        self.assertIn("duplicate topic id q_dup", result.stderr)

    def test_benchmark_rejects_qrel_paths_missing_from_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            topics = base / "topics.jsonl"
            topics.write_text('{"id":"q_missing","query":"deploy 403 token rotation","budget":400}\n', encoding="utf-8")
            qrels = base / "qrels.tsv"
            qrels.write_text("q_missing\tknowledge/missing.md\t3\n", encoding="utf-8")

            result = run_bench("--topics", str(topics), "--qrels", str(qrels))

        self.assertEqual(result.returncode, 2)
        self.assertIn("path does not exist: knowledge/missing.md", result.stderr)

    def test_benchmark_rejects_unknown_qrel_topic_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            topics = base / "topics.jsonl"
            topics.write_text('{"id":"q_known","query":"deploy 403 token rotation","budget":400}\n', encoding="utf-8")
            qrels = base / "qrels.tsv"
            qrels.write_text(
                "q_known\tknowledge/deploy-403.md\t3\n"
                "q_unknown\tknowledge/jwt-clock-skew.md\t3\n",
                encoding="utf-8",
            )

            result = run_bench("--topics", str(topics), "--qrels", str(qrels))

        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown topic id q_unknown", result.stderr)


if __name__ == "__main__":
    unittest.main()
