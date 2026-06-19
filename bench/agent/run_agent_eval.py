from __future__ import annotations

import argparse
import json
import shutil
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


def evaluate_task(root: Path, task: AgentTask, strategy: str) -> dict[str, object]:
    if strategy == "retrieve":
        context, source_paths, used_tokens = _retrieve_context(root, task)
    elif strategy == "grep":
        context, source_paths, used_tokens = _grep_context(root, task)
    else:
        raise ValueError(f"unknown strategy: {strategy}")

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


def _write_output(payload: Mapping[str, object], output: str | None) -> None:
    if not output:
        return
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic L0 agent-eval harness checks.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Validate task schema without executing retrieval.")
    mode.add_argument("--mock", action="store_true", help="Run deterministic context-sufficiency checks.")
    parser.add_argument("--fixture", default=str(ROOT / "bench" / "fixtures" / "vault"))
    parser.add_argument("--tasks", default=str(ROOT / "bench" / "agent" / "tasks.example.jsonl"))
    parser.add_argument("--topics", default=str(ROOT / "bench" / "topics.jsonl"))
    parser.add_argument("--strategy", choices=_STRATEGIES, default="retrieve")
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

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "vault"
        shutil.copytree(fixture, root)
        if args.strategy == "retrieve":
            rebuild_index(root)
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
