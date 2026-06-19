from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_agent_eval(*args: str, env_overrides: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env.setdefault("APOLLOKAIRN_REGISTRY_PATH", str(ROOT / ".cairn" / f"test-registry-{os.getpid()}.json"))
    if env_overrides:
        env.update(env_overrides)
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

    def test_agent_eval_live_invokes_external_provider_and_reports_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            provider = tmp_path / "provider.py"
            request_log = tmp_path / "requests.jsonl"
            provider.write_text(
                "import json, os, sys\n"
                "request = json.load(sys.stdin)\n"
                "with open(os.environ['PROVIDER_REQUEST_LOG'], 'a', encoding='utf-8') as handle:\n"
                "    handle.write(json.dumps(request, sort_keys=True) + '\\n')\n"
                "if request['source_paths']:\n"
                "    response = {\n"
                "        'answer': 'Update the CI secret, rerun the failed deploy job, and write the release log.',\n"
                "        'cited_paths': ['knowledge/deploy-403.md'],\n"
                "        'abstained': False,\n"
                "        'tool_calls': 1,\n"
                "        'input_tokens': 100,\n"
                "        'output_tokens': 20,\n"
                "        'cost_usd': 0.002,\n"
                "    }\n"
                "else:\n"
                "    response = {\n"
                "        'answer': 'I do not have enough context to answer.',\n"
                "        'cited_paths': [],\n"
                "        'abstained': True,\n"
                "        'tool_calls': 1,\n"
                "        'input_tokens': 10,\n"
                "        'output_tokens': 8,\n"
                "        'cost_usd': 0.001,\n"
                "    }\n"
                "print(json.dumps(response))\n",
                encoding="utf-8",
            )
            provider_command = f'"{sys.executable}" "{provider}"'

            result = run_agent_eval(
                "--live",
                "--provider-command",
                provider_command,
                "--provider-name",
                "fake-provider",
                "--model",
                "fake-model",
                "--repeat",
                "2",
                env_overrides={"PROVIDER_REQUEST_LOG": str(request_log)},
            )
            requests = [json.loads(line) for line in request_log.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["suite"], "agent_eval_l2")
        self.assertEqual(payload["mode"], "live")
        self.assertEqual(payload["provider"], "fake-provider")
        self.assertEqual(payload["model"], "fake-model")
        self.assertEqual(payload["repeat"], 2)
        self.assertEqual(payload["tasks"], 2)
        self.assertEqual(payload["runs"], 4)
        self.assertEqual(payload["task_success_rate"], 1.0)
        self.assertEqual(payload["source_path_accuracy"], 1.0)
        self.assertEqual(payload["mean_fact_coverage"], 1.0)
        self.assertEqual(payload["abstention_accuracy"], 1.0)
        self.assertEqual(payload["total_cost_usd"], 0.006)
        self.assertEqual(payload["mean_input_tokens"], 55.0)
        self.assertEqual(payload["mean_output_tokens"], 14.0)

        self.assertEqual(len(requests), 4)
        self.assertIn("context", requests[0])
        self.assertIn("question", requests[0])
        self.assertIn("source_paths", requests[0])
        self.assertNotIn("expected_paths", requests[0])
        self.assertNotIn("expected_facts", requests[0])
        for request in requests:
            self.assertNotIn("expected_paths", request)
            self.assertNotIn("expected_facts", request)
        for run in payload["per_run"]:
            self.assertNotIn("answer", run)
            self.assertNotIn("context", run)

    def test_agent_eval_live_scores_wrong_provider_answers_as_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            provider = Path(tmp) / "provider.py"
            provider.write_text(
                "import json, sys\n"
                "request = json.load(sys.stdin)\n"
                "if request['source_paths']:\n"
                "    response = {\n"
                "        'answer': 'This answer omits the required facts.',\n"
                "        'cited_paths': ['knowledge/wrong.md'],\n"
                "        'abstained': False,\n"
                "        'tool_calls': 1,\n"
                "        'input_tokens': 5,\n"
                "        'output_tokens': 5,\n"
                "        'cost_usd': 0.0,\n"
                "    }\n"
                "else:\n"
                "    response = {\n"
                "        'answer': 'Invented answer for a no-answer task.',\n"
                "        'cited_paths': [],\n"
                "        'abstained': False,\n"
                "        'tool_calls': 1,\n"
                "        'input_tokens': 5,\n"
                "        'output_tokens': 5,\n"
                "        'cost_usd': 0.0,\n"
                "    }\n"
                "print(json.dumps(response))\n",
                encoding="utf-8",
            )
            provider_command = f'"{sys.executable}" "{provider}"'

            result = run_agent_eval("--live", "--provider-command", provider_command)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["task_success_rate"], 0.0)
        self.assertEqual(payload["source_path_accuracy"], 0.0)
        self.assertLess(payload["mean_fact_coverage"], 1.0)
        self.assertEqual(payload["abstention_accuracy"], 0.0)
        self.assertFalse(any(run["task_success"] for run in payload["per_run"]))

    def test_agent_eval_live_requires_citations_for_grounded_answerable_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            provider = Path(tmp) / "provider.py"
            provider.write_text(
                "import json, sys\n"
                "request = json.load(sys.stdin)\n"
                "if request['source_paths']:\n"
                "    response = {\n"
                "        'answer': 'Update the CI secret, rerun the failed deploy job, and write the release log.',\n"
                "        'cited_paths': [],\n"
                "        'abstained': False,\n"
                "    }\n"
                "else:\n"
                "    response = {'answer': 'I do not have enough context to answer.', 'cited_paths': [], 'abstained': True}\n"
                "print(json.dumps(response))\n",
                encoding="utf-8",
            )
            provider_command = f'"{sys.executable}" "{provider}"'

            result = run_agent_eval("--live", "--provider-command", provider_command)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        answerable_run = next(run for run in payload["per_run"] if run["expected_paths"])
        self.assertTrue(answerable_run["task_success"])
        self.assertFalse(answerable_run["grounded"])
        self.assertLess(payload["groundedness_rate"], 1.0)

    def test_agent_eval_live_abstention_accuracy_tracks_provider_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "fixture"
            shutil.copytree(ROOT / "bench" / "fixtures" / "vault", fixture)
            tasks = Path(tmp) / "tasks.jsonl"
            tasks.write_text(
                json.dumps(
                    {
                        "id": "abstain_even_with_context",
                        "question": "deploy 403 token rotation",
                        "expected_paths": [],
                        "expected_facts": [],
                        "expect_abstention": True,
                        "slice": "no_answer",
                        "budget": 800,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            provider = Path(tmp) / "provider.py"
            provider.write_text(
                "import json\n"
                "print(json.dumps({'answer': 'I do not have enough context to answer.', 'cited_paths': [], 'abstained': True}))\n",
                encoding="utf-8",
            )
            provider_command = f'"{sys.executable}" "{provider}"'

            result = run_agent_eval(
                "--live",
                "--provider-command",
                provider_command,
                "--fixture",
                str(fixture),
                "--tasks",
                str(tasks),
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["abstention_accuracy"], 1.0)
        self.assertTrue(payload["per_run"][0]["abstention_correct"])

    def test_agent_eval_live_rejects_invalid_provider_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            provider = Path(tmp) / "provider.py"
            provider.write_text("print('not json')\n", encoding="utf-8")
            provider_command = f'"{sys.executable}" "{provider}"'

            result = run_agent_eval("--live", "--provider-command", provider_command)

        self.assertEqual(result.returncode, 2)
        self.assertIn("provider command returned invalid JSON", result.stderr)

    def test_agent_eval_live_rejects_invalid_provider_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            provider = Path(tmp) / "provider.py"
            provider.write_text("print('{\"answer\": 123, \"cited_paths\": []}')\n", encoding="utf-8")
            provider_command = f'"{sys.executable}" "{provider}"'

            result = run_agent_eval("--live", "--provider-command", provider_command)

        self.assertEqual(result.returncode, 2)
        self.assertIn("provider response field answer must be a string", result.stderr)

    def test_agent_eval_live_rejects_negative_provider_cost(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            provider = Path(tmp) / "provider.py"
            provider.write_text(
                "import json\n"
                "print(json.dumps({\n"
                "    'answer': 'bad cost',\n"
                "    'cited_paths': [],\n"
                "    'abstained': False,\n"
                "    'cost_usd': -0.01,\n"
                "}))\n",
                encoding="utf-8",
            )
            provider_command = f'"{sys.executable}" "{provider}"'

            result = run_agent_eval("--live", "--provider-command", provider_command)

        self.assertEqual(result.returncode, 2)
        self.assertIn("provider response field cost_usd must be non-negative", result.stderr)


if __name__ == "__main__":
    unittest.main()
