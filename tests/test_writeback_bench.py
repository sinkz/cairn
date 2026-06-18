from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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


class WritebackBenchTests(unittest.TestCase):
    def test_writeback_benchmark_outputs_decision_metrics(self) -> None:
        result = run_writeback_bench()

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["suite"], "writeback")
        self.assertGreaterEqual(payload["cases"], 8)
        self.assertEqual(payload["decision_accuracy"], 1.0)
        self.assertEqual(payload["target_path_accuracy"], 1.0)
        self.assertEqual(payload["noop_accuracy"], 1.0)
        self.assertEqual(payload["conflict_detection_rate"], 1.0)
        self.assertEqual(payload["duplicate_avoidance_rate"], 1.0)
        self.assertEqual(payload["idempotency_rate"], 1.0)
        self.assertIn("mean_similarity_margin", payload)
        self.assertTrue({"update", "create", "noop", "conflict"}.issubset(payload["actions"]))
        self.assertTrue({"knowledge", "process", "decision", "pt-BR"}.issubset(payload["categories"]))
        self.assertTrue(all("actual_action" in item for item in payload["per_case"]))

    def test_writeback_benchmark_includes_synonym_and_abbreviation_cases(self) -> None:
        result = run_writeback_bench()

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        cases = {item["id"]: item for item in payload["per_case"]}

        self.assertEqual(cases["prod_access_synonym_update"]["actual_action"], "update")
        self.assertEqual(cases["prod_access_synonym_update"]["target_path"], "processes/production-access-request.md")
        self.assertEqual(cases["ruff_abbreviation_update"]["actual_action"], "update")
        self.assertEqual(cases["ruff_abbreviation_update"]["target_path"], "decisions/use-ruff-formatting.md")

    def test_writeback_benchmark_compare_golden_detects_decision_regression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            golden = Path(tmp) / "golden.json"
            golden.write_text(
                json.dumps(
                    {
                        "cases": {
                            "deploy_403_update": {
                                "actual_action": "create",
                                "target_path": None,
                                "reason": "below_threshold",
                            }
                        }
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = run_writeback_bench("--compare-golden", str(golden))

            self.assertEqual(result.returncode, 1)
            self.assertIn("writeback golden regression", result.stderr)

    def test_writeback_benchmark_quiet_output_is_stable_for_ci(self) -> None:
        result = run_writeback_bench("--quiet", "--compare-golden", "bench/writeback/golden.json")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("writeback ok", result.stdout)
        self.assertIn("decision_accuracy=1.0", result.stdout)
        self.assertIn("duplicate_avoidance=1.0", result.stdout)

    def test_writeback_benchmark_full_json_is_stable_across_runs(self) -> None:
        first = run_writeback_bench()
        second = run_writeback_bench()

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(first.stdout), json.loads(second.stdout))


if __name__ == "__main__":
    unittest.main()
