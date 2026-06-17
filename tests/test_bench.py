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
    return subprocess.run(
        [sys.executable, "bench/run_eval.py", *args],
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
    def test_benchmark_outputs_quality_and_token_metrics_for_harder_suite(self) -> None:
        result = run_bench()

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("mean_recall_at_k", payload)
        self.assertIn("mean_mrr_at_k", payload)
        self.assertIn("mean_ndcg_at_k", payload)
        self.assertIn("returned_tokens", payload)
        self.assertIn("context_reduction", payload)
        self.assertGreaterEqual(payload["topics"], 10)
        self.assertTrue(any(item["mode"] == "passages" for item in payload["per_topic"]))
        passage_topic = next(item for item in payload["per_topic"] if item["mode"] == "passages")
        self.assertEqual(passage_topic["compare"]["mode"], "documents")
        self.assertGreater(passage_topic["compare"]["returned_tokens"], passage_topic["returned_tokens"])
        self.assertGreaterEqual(passage_topic["compare"]["token_reduction"], 0.2)

    def test_benchmark_applies_topic_filters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            fixture = base / "vault"
            fixture.mkdir()
            (fixture / "SCHEMA.md").write_text(
                "# Cairn Schema\n\n"
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


if __name__ == "__main__":
    unittest.main()
