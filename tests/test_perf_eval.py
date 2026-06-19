from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_perf_eval(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env.setdefault("APOLLOKAIRN_REGISTRY_PATH", str(ROOT / ".cairn" / f"test-registry-{os.getpid()}.json"))
    return subprocess.run(
        [sys.executable, "bench/run_perf_eval.py", *args],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class PerfEvalTests(unittest.TestCase):
    def test_perf_eval_outputs_search_retrieve_and_index_metrics(self) -> None:
        result = run_perf_eval(
            "--fixture",
            "bench/fixtures/vault",
            "--topics",
            "bench/topics.jsonl",
            "--repeat",
            "1",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["suite"], "performance")
        self.assertEqual(payload["topics"], 28)
        self.assertGreater(payload["full_index_ms"], 0)
        self.assertGreater(payload["incremental_index_ms"], 0)
        self.assertGreater(payload["index_db_bytes"], 0)
        self.assertEqual(payload["search_ms"]["samples"], 28)
        self.assertEqual(payload["retrieve_ms"]["samples"], 28)
        self.assertGreaterEqual(payload["incremental_index"]["updated"], 1)

    def test_perf_eval_quiet_output_is_stable_for_ci(self) -> None:
        result = run_perf_eval(
            "--fixture",
            "bench/fixtures/vault",
            "--topics",
            "bench/topics.jsonl",
            "--repeat",
            "1",
            "--quiet",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("perf ok", result.stdout)
        self.assertIn("search_p50_ms=", result.stdout)
        self.assertIn("retrieve_p50_ms=", result.stdout)


if __name__ == "__main__":
    unittest.main()
