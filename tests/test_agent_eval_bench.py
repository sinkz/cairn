from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_agent_eval(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env.setdefault("APOLLOKAIRN_REGISTRY_PATH", str(ROOT / ".cairn" / f"test-registry-{os.getpid()}.json"))
    return subprocess.run(
        [sys.executable, "bench/agent/run_agent_eval.py", *args],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class AgentEvalBenchTests(unittest.TestCase):
    def test_agent_eval_dry_run_validates_example_tasks(self) -> None:
        result = run_agent_eval("--dry-run")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["suite"], "agent_eval_l0")
        self.assertEqual(payload["mode"], "dry_run")
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["tasks"], 2)
        self.assertIn("retrieve", payload["strategies"])
        self.assertIn("grep", payload["strategies"])

    def test_agent_eval_mock_measures_context_sufficiency_not_agent_success(self) -> None:
        result = run_agent_eval("--mock")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["mode"], "mock")
        self.assertEqual(payload["strategy"], "retrieve")
        self.assertEqual(payload["context_sufficiency_rate"], 1.0)
        self.assertEqual(payload["source_path_accuracy"], 1.0)
        self.assertEqual(payload["abstention_accuracy"], 1.0)
        self.assertEqual(payload["budget_compliance_rate"], 1.0)
        tasks = {item["id"]: item for item in payload["per_task"]}
        self.assertTrue(tasks["deploy_403_token_rotation"]["context_sufficient"])
        self.assertIn("knowledge/deploy-403.md", tasks["deploy_403_token_rotation"]["source_paths"])
        self.assertTrue(tasks["no_answer_constellation_payroll"]["expect_abstention"])
        self.assertTrue(tasks["no_answer_constellation_payroll"]["abstention_correct"])

    def test_agent_eval_rejects_strategy_inside_task_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tasks = Path(tmp) / "tasks.jsonl"
            tasks.write_text(
                json.dumps(
                    {
                        "id": "bad_strategy",
                        "question": "deploy 403 token rotation",
                        "expected_paths": ["knowledge/deploy-403.md"],
                        "expected_facts": ["CI secret"],
                        "expect_abstention": False,
                        "slice": "exact",
                        "budget": 800,
                        "strategy": "retrieve",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = run_agent_eval("--dry-run", "--tasks", str(tasks))

        self.assertEqual(result.returncode, 2)
        self.assertIn("strategy belongs to the runner", result.stderr)

    def test_agent_eval_rejects_abstention_with_expected_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tasks = Path(tmp) / "tasks.jsonl"
            tasks.write_text(
                json.dumps(
                    {
                        "id": "bad_abstention",
                        "question": "missing thing",
                        "expected_paths": ["knowledge/deploy-403.md"],
                        "expected_facts": [],
                        "expect_abstention": True,
                        "slice": "no_answer",
                        "budget": 400,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = run_agent_eval("--dry-run", "--tasks", str(tasks))

        self.assertEqual(result.returncode, 2)
        self.assertIn("abstention tasks must not include expected paths or facts", result.stderr)

    def test_agent_eval_quiet_output_is_stable_for_ci(self) -> None:
        result = run_agent_eval("--mock", "--quiet")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("agent-eval mock ok", result.stdout)
        self.assertIn("context_sufficiency=1.0", result.stdout)
        self.assertIn("abstention_accuracy=1.0", result.stdout)

    def test_agent_eval_dry_run_validates_large_tasks(self) -> None:
        result = run_agent_eval(
            "--dry-run",
            "--fixture",
            "bench/fixtures/vault-large",
            "--tasks",
            "bench/agent/tasks-large.jsonl",
            "--topics",
            "bench/topics-large.jsonl",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["tasks"], 80)
        self.assertIn("no_answer", payload["slices"])
        self.assertIn("cross_doc", payload["slices"])

    def test_agent_eval_mock_large_tasks_checks_context_sufficiency(self) -> None:
        result = run_agent_eval(
            "--mock",
            "--fixture",
            "bench/fixtures/vault-large",
            "--tasks",
            "bench/agent/tasks-large.jsonl",
            "--topics",
            "bench/topics-large.jsonl",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["tasks"], 80)
        self.assertEqual(payload["context_sufficiency_rate"], 1.0)
        self.assertEqual(payload["source_path_accuracy"], 1.0)
        self.assertEqual(payload["abstention_accuracy"], 1.0)
        no_answer_tasks = [item for item in payload["per_task"] if item["expect_abstention"]]
        self.assertGreaterEqual(len(no_answer_tasks), 4)
        self.assertTrue(all(item["source_paths"] == [] for item in no_answer_tasks))


if __name__ == "__main__":
    unittest.main()
