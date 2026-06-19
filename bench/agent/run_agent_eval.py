from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from cairn.indexer import rebuild_index
from cairn.ranking import query_tokens
from cairn.retriever import approx_tokens, retrieve_packet
from cairn.validate import RESERVED_NAMES


_STRATEGIES = ("retrieve", "grep")
_MODES = ("documents", "passages")
_RANKERS = ("bm25", "rrf", "auto")


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class AgentTask:
    id: str
    question: str
    expected_paths: tuple[str, ...]
    expected_facts: tuple[str, ...]
    expect_abstention: bool
    slice: str
    budget: int
    query_id: str | None = None
    limit: int = 3
    mode: str = "documents"
    ranker: str = "auto"
    type_filter: str | None = None
    tag_filters: tuple[str, ...] = ()
    system_filters: tuple[str, ...] = ()


def _string_tuple(value: object, *, field: str, line_no: int, errors: list[str]) -> tuple[str, ...]:
    if not isinstance(value, list):
        errors.append(f"line {line_no}: {field} must be a list of strings")
        return ()
    out: list[str] = []
    for idx, item in enumerate(value):
        if not isinstance(item, str) or not item:
            errors.append(f"line {line_no}: {field}[{idx}] must be a non-empty string")
            continue
        out.append(item)
    return tuple(out)


def _optional_string_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, str) and value:
        return (value,)
    if isinstance(value, list):
        return tuple(item for item in value if isinstance(item, str) and item)
    return ()


def _positive_int(value: object, *, field: str, line_no: int, default: int, errors: list[str]) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        errors.append(f"line {line_no}: {field} must be a positive integer")
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        errors.append(f"line {line_no}: {field} must be a positive integer")
        return default
    if number <= 0:
        errors.append(f"line {line_no}: {field} must be a positive integer")
        return default
    return number


def _safe_rel_path(value: str) -> bool:
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and "\\" not in value


def _task_from_row(row: object, line_no: int, errors: list[str]) -> AgentTask | None:
    if not isinstance(row, dict):
        errors.append(f"line {line_no}: task must be an object")
        return None
    if "strategy" in row:
        errors.append(f"line {line_no}: strategy belongs to the runner, not to the task")

    task_id = row.get("id")
    question = row.get("question")
    task_slice = row.get("slice")
    if not isinstance(task_id, str) or not task_id:
        errors.append(f"line {line_no}: id must be a non-empty string")
        task_id = f"line_{line_no}"
    if not isinstance(question, str) or not question:
        errors.append(f"line {line_no}: question must be a non-empty string")
        question = ""
    if not isinstance(task_slice, str) or not task_slice:
        errors.append(f"line {line_no}: slice must be a non-empty string")
        task_slice = "general"

    expected_paths = _string_tuple(row.get("expected_paths"), field="expected_paths", line_no=line_no, errors=errors)
    expected_facts = _string_tuple(row.get("expected_facts"), field="expected_facts", line_no=line_no, errors=errors)
    for path in expected_paths:
        if not _safe_rel_path(path):
            errors.append(f"line {line_no}: expected path must stay inside the fixture: {path}")

    expect_abstention = row.get("expect_abstention")
    if not isinstance(expect_abstention, bool):
        errors.append(f"line {line_no}: expect_abstention must be a boolean")
        expect_abstention = False
    if expect_abstention and (expected_paths or expected_facts):
        errors.append(f"line {line_no}: abstention tasks must not include expected paths or facts")
    if not expect_abstention and not expected_paths and not expected_facts:
        errors.append(f"line {line_no}: answerable tasks need at least one expected path or fact")

    query_id = row.get("query_id")
    if query_id is not None and (not isinstance(query_id, str) or not query_id):
        errors.append(f"line {line_no}: query_id must be a non-empty string when present")
        query_id = None

    mode = row.get("mode", "documents")
    if not isinstance(mode, str) or mode not in _MODES:
        errors.append(f"line {line_no}: mode must be one of {', '.join(_MODES)}")
        mode = "documents"
    ranker = row.get("ranker", "auto")
    if not isinstance(ranker, str) or ranker not in _RANKERS:
        errors.append(f"line {line_no}: ranker must be one of {', '.join(_RANKERS)}")
        ranker = "auto"

    type_filter = row.get("type")
    if type_filter is not None and not isinstance(type_filter, str):
        errors.append(f"line {line_no}: type must be a string when present")
        type_filter = None

    return AgentTask(
        id=str(task_id),
        question=str(question),
        expected_paths=expected_paths,
        expected_facts=expected_facts,
        expect_abstention=bool(expect_abstention),
        slice=str(task_slice),
        budget=_positive_int(row.get("budget"), field="budget", line_no=line_no, default=800, errors=errors),
        query_id=query_id,
        limit=_positive_int(row.get("limit"), field="limit", line_no=line_no, default=3, errors=errors),
        mode=mode,
        ranker=ranker,
        type_filter=type_filter,
        tag_filters=_optional_string_tuple(row.get("tag")),
        system_filters=_optional_string_tuple(row.get("system")),
    )


def load_tasks(path: Path) -> list[AgentTask]:
    errors: list[str] = []
    tasks: list[AgentTask] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_no}: invalid JSON: {exc.msg}")
            continue
        task = _task_from_row(row, line_no, errors)
        if task is not None:
            tasks.append(task)
    if not tasks:
        errors.append(f"{path}: expected at least one task")
    if errors:
        raise ValueError("\n".join(errors))
    return tasks


def load_topic_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    topic_ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if isinstance(row, dict) and isinstance(row.get("id"), str):
            topic_ids.add(str(row["id"]))
    return topic_ids


def validate_task_references(tasks: Sequence[AgentTask], fixture: Path, topic_ids: set[str]) -> None:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for task in tasks:
        if task.id in seen_ids:
            errors.append(f"task {task.id}: duplicate id")
        seen_ids.add(task.id)
        if task.query_id and topic_ids and task.query_id not in topic_ids:
            errors.append(f"task {task.id}: query_id does not exist: {task.query_id}")
        for rel in task.expected_paths:
            if not (fixture / rel).is_file():
                errors.append(f"task {task.id}: expected path does not exist: {rel}")
    if errors:
        raise ValueError("\n".join(errors))


def _rate(values: Sequence[bool]) -> float:
    if not values:
        return 1.0
    return round(sum(1 for value in values if value) / len(values), 4)


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 1.0
    return round(sum(values) / len(values), 4)


def _stddev(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return round(variance**0.5, 4)


def _concept_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in root.rglob("*.md"):
        rel_parts = path.relative_to(root).parts
        if ".cairn" in rel_parts or "_templates" in rel_parts:
            continue
        if path.name in RESERVED_NAMES:
            continue
        out.append(path)
    return sorted(out)


def _grep_context(root: Path, task: AgentTask) -> tuple[str, list[str], int]:
    tokens = [token.casefold() for token in query_tokens(task.question)]
    if not tokens:
        return "", [], 0
    max_chars = task.budget * 4
    parts: list[str] = []
    source_paths: list[str] = []
    used_chars = 0
    for path in _concept_files(root):
        text = path.read_text(encoding="utf-8")
        haystack = text.casefold()
        if not all(token in haystack for token in tokens):
            continue
        rel = path.relative_to(root).as_posix()
        prefix = f"path: {rel}\ncontent:\n"
        separator = "\n---\n" if parts else ""
        remaining = max_chars - used_chars - len(separator) - len(prefix)
        if remaining <= 0:
            break
        content = text[:remaining]
        block = separator + prefix + content
        parts.append(block)
        source_paths.append(rel)
        used_chars += len(block)
        if len(source_paths) >= task.limit:
            break
    context = "".join(parts)
    return context, source_paths, approx_tokens(context)


def _retrieve_context(root: Path, task: AgentTask) -> tuple[str, list[str], int]:
    packet = retrieve_packet(
        root,
        task.question,
        limit=task.limit,
        budget_tokens=task.budget,
        mode=task.mode,
        type_filter=task.type_filter,
        tag_filters=task.tag_filters,
        system_filters=task.system_filters,
        ranker=task.ranker,
    )
    return packet.context, [source.path for source in packet.sources], packet.used_tokens


def _context_for_task(root: Path, task: AgentTask, strategy: str) -> tuple[str, list[str], int]:
    if strategy == "retrieve":
        return _retrieve_context(root, task)
    if strategy == "grep":
        return _grep_context(root, task)
    raise ValueError(f"unknown strategy: {strategy}")


def evaluate_task(root: Path, task: AgentTask, strategy: str) -> dict[str, object]:
    context, source_paths, used_tokens = _context_for_task(root, task, strategy)

    context_folded = context.casefold()
    matched_facts = [fact for fact in task.expected_facts if fact.casefold() in context_folded]
    missing_facts = [fact for fact in task.expected_facts if fact.casefold() not in context_folded]
    path_sufficient = all(path in source_paths for path in task.expected_paths)
    fact_coverage = len(matched_facts) / len(task.expected_facts) if task.expected_facts else 1.0
    facts_sufficient = not missing_facts
    abstention_correct = not source_paths and used_tokens == 0
    context_sufficient = abstention_correct if task.expect_abstention else path_sufficient and facts_sufficient

    return {
        "id": task.id,
        "query_id": task.query_id,
        "slice": task.slice,
        "expected_paths": list(task.expected_paths),
        "source_paths": source_paths,
        "expected_facts": list(task.expected_facts),
        "matched_facts": matched_facts,
        "missing_facts": missing_facts,
        "expect_abstention": task.expect_abstention,
        "abstention_correct": abstention_correct if task.expect_abstention else None,
        "path_sufficient": path_sufficient,
        "facts_sufficient": facts_sufficient,
        "fact_coverage": round(fact_coverage, 4),
        "context_sufficient": context_sufficient,
        "returned_tokens": used_tokens,
        "budget_tokens": task.budget,
        "within_budget": used_tokens <= task.budget,
    }


def _optional_string_list(value: object, *, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ProviderError(f"provider response field {field} must be a list of strings")
    out: list[str] = []
    for idx, item in enumerate(value):
        if not isinstance(item, str):
            raise ProviderError(f"provider response field {field}[{idx}] must be a string")
        out.append(item)
    return out


def _optional_number(value: object, *, field: str, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProviderError(f"provider response field {field} must be a number")
    number = float(value)
    if number < 0:
        raise ProviderError(f"provider response field {field} must be non-negative")
    return number


def _optional_int(value: object, *, field: str, default: int) -> int:
    number = _optional_number(value, field=field, default=float(default))
    if number < 0:
        raise ProviderError(f"provider response field {field} must be non-negative")
    return int(number)


def _run_provider_command(command: str, request: Mapping[str, object], timeout: float) -> dict[str, object]:
    try:
        result = subprocess.run(
            command,
            input=json.dumps(request, ensure_ascii=False),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProviderError(f"provider command timed out after {timeout:g}s") from exc
    if result.returncode != 0:
        stderr = result.stderr.strip()
        detail = f": {stderr}" if stderr else ""
        raise ProviderError(f"provider command failed with exit code {result.returncode}{detail}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ProviderError(f"provider command returned invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ProviderError("provider command JSON must be an object")
    return payload


def evaluate_live_run(
    root: Path,
    task: AgentTask,
    strategy: str,
    *,
    repetition: int,
    provider_command: str,
    provider_name: str,
    model: str,
    temperature: float,
    timeout: float,
) -> dict[str, object]:
    context, source_paths, used_tokens = _context_for_task(root, task, strategy)
    request = {
        "task_id": task.id,
        "query_id": task.query_id,
        "slice": task.slice,
        "question": task.question,
        "context": context,
        "source_paths": source_paths,
        "strategy": strategy,
        "mode": task.mode,
        "ranker": task.ranker,
        "budget_tokens": task.budget,
        "repetition": repetition,
        "provider": provider_name,
        "model": model,
        "temperature": temperature,
    }
    response = _run_provider_command(provider_command, request, timeout)
    answer = response.get("answer")
    if not isinstance(answer, str):
        raise ProviderError("provider response field answer must be a string")
    cited_paths = _optional_string_list(response.get("cited_paths"), field="cited_paths")
    abstained = response.get("abstained", False)
    if not isinstance(abstained, bool):
        raise ProviderError("provider response field abstained must be a boolean")

    input_tokens = _optional_int(
        response.get("input_tokens"),
        field="input_tokens",
        default=approx_tokens(task.question) + used_tokens,
    )
    output_tokens = _optional_int(response.get("output_tokens"), field="output_tokens", default=approx_tokens(answer))
    tool_calls = _optional_int(response.get("tool_calls"), field="tool_calls", default=1)
    cost_usd = _optional_number(response.get("cost_usd"), field="cost_usd", default=0.0)

    answer_folded = answer.casefold()
    matched_facts = [fact for fact in task.expected_facts if fact.casefold() in answer_folded]
    missing_facts = [fact for fact in task.expected_facts if fact.casefold() not in answer_folded]
    path_sufficient = all(path in cited_paths or path in answer for path in task.expected_paths)
    fact_coverage = len(matched_facts) / len(task.expected_facts) if task.expected_facts else 1.0
    facts_sufficient = not missing_facts
    abstention_correct = abstained and not cited_paths
    answer_sufficient = facts_sufficient if task.expected_facts else path_sufficient
    task_success = abstention_correct if task.expect_abstention else answer_sufficient
    grounded = abstention_correct if task.expect_abstention else bool(cited_paths) and all(path in source_paths for path in cited_paths)

    return {
        "id": task.id,
        "query_id": task.query_id,
        "slice": task.slice,
        "repetition": repetition,
        "expected_paths": list(task.expected_paths),
        "source_paths": source_paths,
        "cited_paths": cited_paths,
        "expected_facts": list(task.expected_facts),
        "matched_facts": matched_facts,
        "missing_facts": missing_facts,
        "expect_abstention": task.expect_abstention,
        "abstained": abstained,
        "abstention_correct": abstention_correct if task.expect_abstention else None,
        "path_sufficient": path_sufficient,
        "facts_sufficient": facts_sufficient,
        "fact_coverage": round(fact_coverage, 4),
        "grounded": grounded,
        "task_success": task_success,
        "context_tokens": used_tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "tool_calls": tool_calls,
        "cost_usd": round(cost_usd, 6),
        "budget_tokens": task.budget,
        "within_budget": used_tokens <= task.budget,
    }


def summarize_mock(per_task: Sequence[dict[str, object]], strategy: str) -> dict[str, object]:
    path_tasks = [item for item in per_task if item["expected_paths"]]
    abstention_tasks = [item for item in per_task if item["expect_abstention"]]
    return {
        "suite": "agent_eval_l0",
        "mode": "mock",
        "strategy": strategy,
        "tasks": len(per_task),
        "slices": sorted({str(item["slice"]) for item in per_task}),
        "context_sufficiency_rate": _rate([bool(item["context_sufficient"]) for item in per_task]),
        "source_path_accuracy": _rate([bool(item["path_sufficient"]) for item in path_tasks]),
        "mean_fact_coverage": _mean([float(item["fact_coverage"]) for item in per_task]),
        "abstention_accuracy": _rate([bool(item["abstention_correct"]) for item in abstention_tasks]),
        "budget_compliance_rate": _rate([bool(item["within_budget"]) for item in per_task]),
        "returned_tokens": sum(int(item["returned_tokens"]) for item in per_task),
        "per_task": list(per_task),
    }


def summarize_dry_run(tasks: Sequence[AgentTask]) -> dict[str, object]:
    return {
        "suite": "agent_eval_l0",
        "mode": "dry_run",
        "valid": True,
        "tasks": len(tasks),
        "slices": sorted({task.slice for task in tasks}),
        "strategies": list(_STRATEGIES),
    }


def summarize_live(
    per_run: Sequence[dict[str, object]],
    *,
    tasks: Sequence[AgentTask],
    strategy: str,
    provider_name: str,
    model: str,
    repeat: int,
    temperature: float,
) -> dict[str, object]:
    path_runs = [item for item in per_run if item["expected_paths"]]
    abstention_runs = [item for item in per_run if item["expect_abstention"]]
    input_tokens = [float(item["input_tokens"]) for item in per_run]
    output_tokens = [float(item["output_tokens"]) for item in per_run]
    tool_calls = [float(item["tool_calls"]) for item in per_run]
    costs = [float(item["cost_usd"]) for item in per_run]
    return {
        "suite": "agent_eval_l2",
        "mode": "live",
        "strategy": strategy,
        "provider": provider_name,
        "model": model,
        "temperature": temperature,
        "repeat": repeat,
        "tasks": len(tasks),
        "runs": len(per_run),
        "slices": sorted({task.slice for task in tasks}),
        "task_success_rate": _rate([bool(item["task_success"]) for item in per_run]),
        "source_path_accuracy": _rate([bool(item["path_sufficient"]) for item in path_runs]),
        "mean_fact_coverage": _mean([float(item["fact_coverage"]) for item in per_run]),
        "abstention_accuracy": _rate([bool(item["abstention_correct"]) for item in abstention_runs]),
        "groundedness_rate": _rate([bool(item["grounded"]) for item in per_run]),
        "budget_compliance_rate": _rate([bool(item["within_budget"]) for item in per_run]),
        "mean_input_tokens": _mean(input_tokens),
        "stddev_input_tokens": _stddev(input_tokens),
        "mean_output_tokens": _mean(output_tokens),
        "stddev_output_tokens": _stddev(output_tokens),
        "mean_tool_calls": _mean(tool_calls),
        "stddev_tool_calls": _stddev(tool_calls),
        "total_cost_usd": round(sum(costs), 6),
        "mean_cost_usd": round(sum(costs) / len(costs), 6) if costs else 0.0,
        "per_run": list(per_run),
    }


def _write_output(payload: Mapping[str, object], output: str | None) -> None:
    if not output:
        return
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run agent-eval harness checks.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Validate task schema without executing retrieval.")
    mode.add_argument("--mock", action="store_true", help="Run deterministic context-sufficiency checks.")
    mode.add_argument("--live", action="store_true", help="Run optional L2 provider-command evaluation.")
    parser.add_argument("--fixture", default=str(ROOT / "bench" / "fixtures" / "vault"))
    parser.add_argument("--tasks", default=str(ROOT / "bench" / "agent" / "tasks.example.jsonl"))
    parser.add_argument("--topics", default=str(ROOT / "bench" / "topics.jsonl"))
    parser.add_argument("--strategy", choices=_STRATEGIES, default="retrieve")
    parser.add_argument("--provider-command", help="External command that reads request JSON on stdin and writes response JSON.")
    parser.add_argument("--provider-name", default="external-command")
    parser.add_argument("--model", default="external")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--provider-timeout", type=float, default=60.0)
    parser.add_argument("--min-context-sufficiency", type=float, default=1.0)
    parser.add_argument("--output")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    fixture = Path(args.fixture)
    try:
        tasks = load_tasks(Path(args.tasks))
        validate_task_references(tasks, fixture, load_topic_ids(Path(args.topics)))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"agent eval error: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        payload = summarize_dry_run(tasks)
        _write_output(payload, args.output)
        if args.quiet:
            print(f"agent-eval dry-run ok tasks={payload['tasks']}")
        else:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.live:
        if not args.provider_command:
            print("agent eval error: --live requires --provider-command", file=sys.stderr)
            return 2
        if args.repeat <= 0:
            print("agent eval error: --repeat must be a positive integer", file=sys.stderr)
            return 2
        if args.provider_timeout <= 0:
            print("agent eval error: --provider-timeout must be positive", file=sys.stderr)
            return 2

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "vault"
        shutil.copytree(fixture, root)
        if args.strategy == "retrieve":
            rebuild_index(root)
        if args.live:
            per_run: list[dict[str, object]] = []
            try:
                for repetition in range(1, args.repeat + 1):
                    for task in tasks:
                        per_run.append(
                            evaluate_live_run(
                                root,
                                task,
                                args.strategy,
                                repetition=repetition,
                                provider_command=args.provider_command,
                                provider_name=args.provider_name,
                                model=args.model,
                                temperature=args.temperature,
                                timeout=args.provider_timeout,
                            )
                        )
            except ProviderError as exc:
                print(f"agent eval error: {exc}", file=sys.stderr)
                return 2
            payload = summarize_live(
                per_run,
                tasks=tasks,
                strategy=args.strategy,
                provider_name=args.provider_name,
                model=args.model,
                repeat=args.repeat,
                temperature=args.temperature,
            )
            _write_output(payload, args.output)
            if args.quiet:
                print(
                    "agent-eval live ok "
                    f"provider={payload['provider']} "
                    f"model={payload['model']} "
                    f"tasks={payload['tasks']} "
                    f"repeat={payload['repeat']} "
                    f"task_success={payload['task_success_rate']} "
                    f"cost_usd={payload['total_cost_usd']}"
                )
            else:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        per_task = [evaluate_task(root, task, args.strategy) for task in tasks]

    payload = summarize_mock(per_task, args.strategy)
    _write_output(payload, args.output)
    if args.quiet:
        print(
            "agent-eval mock ok "
            f"strategy={args.strategy} "
            f"tasks={payload['tasks']} "
            f"context_sufficiency={payload['context_sufficiency_rate']} "
            f"abstention_accuracy={payload['abstention_accuracy']}"
        )
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    if float(payload["context_sufficiency_rate"]) < args.min_context_sufficiency:
        return 1
    if float(payload["budget_compliance_rate"]) < 1.0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
