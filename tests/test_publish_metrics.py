from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_publish_metrics(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env.setdefault("APOLLOKAIRN_REGISTRY_PATH", str(ROOT / ".cairn" / f"test-registry-{os.getpid()}.json"))
    return subprocess.run(
        [sys.executable, "bench/publish_metrics.py", *args],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class PublishMetricsTests(unittest.TestCase):
    def test_publish_metrics_updates_public_json_history_and_deltas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "benchmarks.json"

            result = run_publish_metrics(
                "--input",
                "docs/data/benchmarks.json",
                "--output",
                str(output),
                "--date",
                "2026-06-18",
                "--retrieval-label",
                "BM25 + glossary aliases",
                "--writeback-label",
                "similarity-threshold-v1",
                "--tests",
                "166",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["generated_by"], "bench/publish_metrics.py")
            current_metrics = {metric["id"]: metric for metric in data["current"]["metrics"]}
            self.assertEqual(current_metrics["tests"]["value"], 166)

            retrieval = next(suite for suite in data["suites"] if suite["id"] == "retrieval")
            retrieval_keys = [(row["date"], row["label"]) for row in retrieval["history"]]
            self.assertEqual(retrieval_keys.count(("2026-06-18", "BM25 + glossary aliases")), 1)
            self.assertEqual(retrieval["history"][-1]["ndcg_at_3"], 0.9941)

            metrics = {metric["id"]: metric for metric in retrieval["current"]["metrics"]}
            self.assertEqual(metrics["recall_at_3"]["value"], 1.0)
            self.assertEqual(metrics["context_reduction"]["value"], 0.9183)
            self.assertEqual(metrics["ndcg_at_3"]["delta"]["value"], 0.001)
            self.assertEqual(metrics["ndcg_at_3"]["delta"]["direction"], "up")
            self.assertEqual(metrics["ndcg_at_3"]["delta"]["trend"], "better")
            self.assertEqual(metrics["context_reduction"]["delta"]["direction"], "down")
            corpus = retrieval["current"]["corpus"]
            self.assertEqual(corpus["markdown_files"], 25)
            self.assertEqual(corpus["topics"], 28)
            self.assertEqual(corpus["qrel_rows"], 31)
            self.assertEqual(data["current"]["corpus"], corpus)
            retrieval_row = next(
                row for row in retrieval["history"]
                if row["date"] == "2026-06-18" and row["label"] == "BM25 + glossary aliases"
            )
            self.assertEqual(retrieval_row["corpus"]["positive_qrels"], 31)
            legacy_row = next(
                row for row in data["history"]
                if row["date"] == "2026-06-18" and row["label"] == "BM25 + glossary aliases"
            )
            self.assertEqual(legacy_row["corpus"], retrieval_row["corpus"])

            writeback = next(suite for suite in data["suites"] if suite["id"] == "writeback")
            writeback_metrics = {metric["id"]: metric["value"] for metric in writeback["current"]["metrics"]}
            self.assertGreaterEqual(writeback_metrics["writeback_cases"], 9)
            self.assertEqual(writeback_metrics["decision_accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()
