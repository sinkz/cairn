from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cairn.indexer import rebuild_index, search, search_passages
from cairn.retriever import approx_tokens, retrieve


@dataclass(frozen=True)
class Topic:
    id: str
    query: str
    budget: int
    category: str = "general"
    limit: int | None = None
    type_filter: str | None = None
    tag_filters: tuple[str, ...] = ()
    system_filters: tuple[str, ...] = ()
    mode: str = "documents"
    ranker: str = "bm25"
    compare_mode: str | None = None
    compare_ranker: str | None = None


def _string_list(value: object) -> tuple[str, ...]:
    if isinstance(value, str) and value:
        return (value,)
    if isinstance(value, list):
        return tuple(item for item in value if isinstance(item, str) and item)
    return ()


def load_topics(path: Path) -> list[Topic]:
    topics: list[Topic] = []
    errors: list[str] = []
    seen_ids: set[str] = set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}:{line_no}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(row, dict):
            errors.append(f"{path}:{line_no}: topic must be an object")
            continue
        topic_id = row.get("id")
        query = row.get("query")
        if not isinstance(topic_id, str) or not topic_id:
            errors.append(f"{path}:{line_no}: id must be a non-empty string")
            continue
        if topic_id in seen_ids:
            errors.append(f"{path}:{line_no}: duplicate topic id {topic_id}")
        seen_ids.add(topic_id)
        if not isinstance(query, str) or not query:
            errors.append(f"{path}:{line_no}: query must be a non-empty string")
            continue
        budget = row.get("budget", 600)
        try:
            budget_value = int(budget)
        except (TypeError, ValueError):
            errors.append(f"{path}:{line_no}: budget must be a positive integer")
            budget_value = 600
        if budget_value <= 0:
            errors.append(f"{path}:{line_no}: budget must be a positive integer")
            budget_value = 600
        limit = None
        if "limit" in row:
            try:
                limit = int(row["limit"])
            except (TypeError, ValueError):
                errors.append(f"{path}:{line_no}: limit must be a positive integer")
            else:
                if limit <= 0:
                    errors.append(f"{path}:{line_no}: limit must be a positive integer")
        topics.append(
            Topic(
                id=topic_id,
                query=query,
                budget=budget_value,
                category=row.get("category", "general") if isinstance(row.get("category", "general"), str) else "general",
                limit=limit,
                type_filter=row.get("type") if isinstance(row.get("type"), str) else None,
                tag_filters=_string_list(row.get("tag")),
                system_filters=_string_list(row.get("system")),
                mode=row.get("mode", "documents") if isinstance(row.get("mode", "documents"), str) else "documents",
                ranker=row.get("ranker", "bm25") if isinstance(row.get("ranker", "bm25"), str) else "bm25",
                compare_mode=row.get("compare_mode") if isinstance(row.get("compare_mode"), str) else None,
                compare_ranker=row.get("compare_ranker") if isinstance(row.get("compare_ranker"), str) else None,
            )
        )
        if topics[-1].mode not in {"documents", "passages"}:
            errors.append(f"{path}:{line_no}: mode must be 'documents' or 'passages'")
        if topics[-1].ranker not in {"bm25", "rrf"}:
            errors.append(f"{path}:{line_no}: ranker must be 'bm25' or 'rrf'")
        if topics[-1].compare_mode and topics[-1].compare_mode not in {"documents", "passages"}:
            errors.append(f"{path}:{line_no}: compare_mode must be 'documents' or 'passages'")
        if topics[-1].compare_ranker and topics[-1].compare_ranker not in {"bm25", "rrf"}:
            errors.append(f"{path}:{line_no}: compare_ranker must be 'bm25' or 'rrf'")
    if not topics:
        errors.append(f"{path}: expected at least one topic")
    if errors:
        raise ValueError("\n".join(errors))
    return topics


def load_qrels(path: Path) -> dict[str, dict[str, int]]:
    qrels: dict[str, dict[str, int]] = {}
    errors: list[str] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip() or line.startswith("#"):
            continue
        if line_no == 1 and line.casefold().startswith("query_id\t"):
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            errors.append(f"{path}:{line_no}: qrel must have query_id, path, relevance")
            continue
        qid, doc, rel_text = parts
        if not qid or not doc:
            errors.append(f"{path}:{line_no}: query_id and path must be non-empty")
            continue
        try:
            rel = int(rel_text)
        except ValueError:
            errors.append(f"{path}:{line_no}: relevance must be an integer")
            continue
        if rel < 0:
            errors.append(f"{path}:{line_no}: relevance must be non-negative")
            continue
        qrels.setdefault(qid, {})[doc] = rel
    if errors:
        raise ValueError("\n".join(errors))
    return qrels


def _safe_qrel_path(value: str) -> bool:
    path = Path(value)
    return not path.is_absolute() and ".." not in Path(value).parts and "\\" not in value


def validate_inputs(root: Path, topics: Sequence[Topic], qrels: dict[str, dict[str, int]]) -> None:
    errors: list[str] = []
    topic_ids = {topic.id for topic in topics}
    answerable_topic_ids = {topic.id for topic in topics if topic.category != "no_answer"}
    for topic_id in sorted(answerable_topic_ids - set(qrels)):
        errors.append(f"topic {topic_id}: missing qrels")
    for topic_id in sorted(set(qrels) - topic_ids):
        errors.append(f"qrels: unknown topic id {topic_id}")
    no_answer_ids = topic_ids - answerable_topic_ids
    for topic_id in sorted(no_answer_ids):
        if any(rel > 0 for rel in qrels.get(topic_id, {}).values()):
            errors.append(f"topic {topic_id}: no_answer topics must not have positive qrels")
    for topic_id, docs in sorted(qrels.items()):
        for rel, relevance in sorted(docs.items()):
            if not _safe_qrel_path(rel):
                errors.append(f"qrels {topic_id}: path must stay inside fixture: {rel}")
                continue
            if not (root / rel).is_file():
                errors.append(f"qrels {topic_id}: path does not exist: {rel}")
            if relevance > 3:
                errors.append(f"qrels {topic_id}: relevance must be between 0 and 3")
    if errors:
        raise ValueError("\n".join(errors))


def dcg(rels: list[int]) -> float:
    total = 0.0
    for idx, rel in enumerate(rels, start=1):
        total += ((2**rel) - 1) / math.log2(idx + 1)
    return total


def _filters(topic: Topic) -> dict[str, object]:
    out: dict[str, object] = {}
    if topic.type_filter:
        out["type"] = topic.type_filter
    if topic.tag_filters:
        out["tag"] = list(topic.tag_filters)
    if topic.system_filters:
        out["system"] = list(topic.system_filters)
    return out


def _unique_ordered(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _topic_docs(root: Path, topic: Topic, limit: int, mode: str, ranker: str) -> list[str]:
    if mode == "passages":
        passage_results = search_passages(
            root,
            topic.query,
            limit=limit,
            type_filter=topic.type_filter,
            tag_filters=topic.tag_filters,
            system_filters=topic.system_filters,
            ranker=ranker,
        )
        return _unique_ordered(result.path for result in passage_results)
    results = search(
        root,
        topic.query,
        limit=limit,
        type_filter=topic.type_filter,
        tag_filters=topic.tag_filters,
        system_filters=topic.system_filters,
        ranker=ranker,
    )
    return [result.path for result in results]


def _quality(docs: Sequence[str], relevant: dict[str, int], limit: int) -> dict[str, float]:
    relevant_docs = {doc for doc, rel in relevant.items() if rel > 0}
    retrieved_relevant = [doc for doc in docs[:limit] if doc in relevant_docs]
    first_rank = next((idx for idx, doc in enumerate(docs[:limit], start=1) if doc in relevant_docs), None)
    gains = [relevant.get(doc, 0) for doc in docs[:limit]]
    ideal = sorted(relevant.values(), reverse=True)[:limit]
    ndcg = dcg(gains) / dcg(ideal) if ideal and dcg(ideal) else 0.0
    return {
        "recall_at_k": len(retrieved_relevant) / len(relevant_docs) if relevant_docs else 1.0,
        "mrr_at_k": 1 / first_rank if first_rank else 0.0,
        "ndcg_at_k": ndcg,
    }


def evaluate_topic(root: Path, topic: Topic, relevant: dict[str, int], default_limit: int) -> dict[str, object]:
    limit = topic.limit or default_limit
    docs = _topic_docs(root, topic, limit, topic.mode, topic.ranker)
    quality = _quality(docs, relevant, limit)
    packet = retrieve(
        root,
        topic.query,
        limit=limit,
        budget_tokens=topic.budget,
        mode=topic.mode,
        type_filter=topic.type_filter,
        tag_filters=topic.tag_filters,
        system_filters=topic.system_filters,
        ranker=topic.ranker,
    )
    returned_tokens = approx_tokens(packet)
    out: dict[str, object] = {
        "id": topic.id,
        "query": topic.query,
        "category": topic.category,
        "mode": topic.mode,
        "ranker": topic.ranker,
        "limit": limit,
        "filters": _filters(topic),
        "docs": docs,
        **quality,
        "returned_tokens": returned_tokens,
        "budget_tokens": topic.budget,
        "within_budget": returned_tokens <= topic.budget,
    }
    if topic.compare_mode or topic.compare_ranker:
        compare_mode = topic.compare_mode or topic.mode
        compare_ranker = topic.compare_ranker or "bm25"
        compare_docs = _topic_docs(root, topic, limit, compare_mode, compare_ranker)
        compare_quality = _quality(compare_docs, relevant, limit)
        compare_packet = retrieve(
            root,
            topic.query,
            limit=limit,
            budget_tokens=topic.budget,
            mode=compare_mode,
            type_filter=topic.type_filter,
            tag_filters=topic.tag_filters,
            system_filters=topic.system_filters,
            ranker=compare_ranker,
        )
        compare_tokens = approx_tokens(compare_packet)
        reduction = 0.0 if compare_tokens == 0 else 1 - (returned_tokens / compare_tokens)
        out["compare"] = {
            "mode": compare_mode,
            "ranker": compare_ranker,
            "docs": compare_docs,
            **compare_quality,
            "returned_tokens": compare_tokens,
            "token_reduction": round(reduction, 4),
        }
    return out


def corpus_tokens(root: Path) -> int:
    total = 0
    for path in root.rglob("*.md"):
        if ".cairn" in path.parts:
            continue
        total += approx_tokens(path.read_text(encoding="utf-8"))
    return total


def corpus_metadata(root: Path, topics: Sequence[Topic], qrels: dict[str, dict[str, int]]) -> dict[str, object]:
    markdown_files = [
        path for path in root.rglob("*.md")
        if ".cairn" not in path.relative_to(root).parts
    ]
    answerable_topics = [topic for topic in topics if topic.category != "no_answer"]
    positive_relevance_counts = [
        sum(1 for rel in qrels.get(topic.id, {}).values() if rel > 0)
        for topic in answerable_topics
    ]
    topics_by_category: dict[str, int] = {}
    for topic in topics:
        topics_by_category[topic.category] = topics_by_category.get(topic.category, 0) + 1
    positive_qrels = sum(
        1 for docs in qrels.values() for rel in docs.values()
        if rel > 0
    )
    qrel_rows = sum(len(docs) for docs in qrels.values())
    mean_positive = (
        sum(positive_relevance_counts) / len(positive_relevance_counts)
        if positive_relevance_counts
        else 0.0
    )
    return {
        "markdown_files": len(markdown_files),
        "topics": len(topics),
        "qrel_rows": qrel_rows,
        "positive_qrels": positive_qrels,
        "answerable_topics": len(answerable_topics),
        "no_answer_topics": len(topics) - len(answerable_topics),
        "mean_positive_qrels_per_answerable_topic": round(mean_positive, 4),
        "slices": sorted(topics_by_category),
        "topics_by_slice": dict(sorted(topics_by_category.items())),
    }


def run_map(per_topic: Sequence[dict[str, object]]) -> dict[str, list[str]]:
    return {str(item["id"]): list(item["docs"]) for item in per_topic}


def compare_golden(actual: dict[str, list[str]], golden_path: Path) -> list[str]:
    expected = json.loads(golden_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if not isinstance(expected, dict):
        return [f"golden regression: {golden_path} must contain an object"]
    for qid, expected_docs in expected.items():
        if not isinstance(expected_docs, list):
            failures.append(f"golden regression: {qid} expected docs must be a list")
            continue
        actual_docs = actual.get(str(qid), [])
        expected_prefix = [doc for doc in expected_docs if isinstance(doc, str)]
        if actual_docs[: len(expected_prefix)] != expected_prefix:
            failures.append(
                "golden regression: "
                f"{qid} expected prefix {expected_prefix}, got {actual_docs[:len(expected_prefix)]}"
            )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic Cairn search benchmarks.")
    parser.add_argument("--fixture", default=str(ROOT / "bench" / "fixtures" / "vault"))
    parser.add_argument("--topics", default=str(ROOT / "bench" / "topics.jsonl"))
    parser.add_argument("--qrels", default=str(ROOT / "bench" / "qrels.tsv"))
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--min-recall", type=float, default=0.9)
    parser.add_argument("--min-mrr", type=float, default=0.8)
    parser.add_argument("--min-ndcg", type=float, default=0.8)
    parser.add_argument("--write-golden")
    parser.add_argument("--compare-golden")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    try:
        topics = load_topics(Path(args.topics))
        qrels = load_qrels(Path(args.qrels))
        validate_inputs(Path(args.fixture), topics, qrels)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"benchmark input error: {exc}", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "vault"
        shutil.copytree(Path(args.fixture), root)
        rebuild_index(root)
        per_topic = [
            evaluate_topic(root, topic, qrels.get(topic.id, {}), default_limit=args.limit)
            for topic in topics
        ]
        full_tokens = corpus_tokens(root)
        mean_recall = sum(float(item["recall_at_k"]) for item in per_topic) / len(per_topic)
        mean_mrr = sum(float(item["mrr_at_k"]) for item in per_topic) / len(per_topic)
        mean_ndcg = sum(float(item["ndcg_at_k"]) for item in per_topic) / len(per_topic)
        returned_tokens = sum(int(item["returned_tokens"]) for item in per_topic)
        full_context_tokens = full_tokens * len(per_topic)
        compared = [
            item
            for item in per_topic
            if isinstance(item.get("compare"), dict)
            and int(item["compare"]["returned_tokens"]) > int(item["returned_tokens"])
        ]
        comparison_candidate_tokens = sum(int(item["returned_tokens"]) for item in compared)
        comparison_baseline_tokens = sum(int(item["compare"]["returned_tokens"]) for item in compared)
        comparison_reduction = (
            1 - (comparison_candidate_tokens / comparison_baseline_tokens)
            if comparison_baseline_tokens
            else 0
        )
        output = {
            "topics": len(topics),
            "limit": args.limit,
            "corpus": corpus_metadata(root, topics, qrels),
            "mean_recall_at_k": round(mean_recall, 4),
            "mean_mrr_at_k": round(mean_mrr, 4),
            "mean_ndcg_at_k": round(mean_ndcg, 4),
            "full_context_tokens": full_context_tokens,
            "returned_tokens": returned_tokens,
            "context_reduction": round(1 - (returned_tokens / full_context_tokens), 4)
            if full_context_tokens
            else 0,
            "comparison": {
                "topics": len(compared),
                "candidate_tokens": comparison_candidate_tokens,
                "baseline_tokens": comparison_baseline_tokens,
                "token_reduction": round(comparison_reduction, 4),
            },
            "per_topic": per_topic,
        }
    actual_run = run_map(per_topic)
    if args.write_golden:
        golden_path = Path(args.write_golden)
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(json.dumps(actual_run, indent=2) + "\n", encoding="utf-8")
    golden_failures: list[str] = []
    if args.compare_golden:
        golden_failures = compare_golden(actual_run, Path(args.compare_golden))
        for failure in golden_failures:
            print(failure, file=sys.stderr)
    if args.quiet:
        print(
            "bench ok "
            f"recall@{args.limit}={output['mean_recall_at_k']} "
            f"mrr@{args.limit}={output['mean_mrr_at_k']} "
            f"ndcg@{args.limit}={output['mean_ndcg_at_k']} "
            f"context_reduction={output['context_reduction']} "
            f"comparison_reduction={output['comparison']['token_reduction']}"
        )
    else:
        print(json.dumps(output, indent=2))
    if golden_failures:
        return 1
    if mean_recall < args.min_recall or mean_mrr < args.min_mrr or mean_ndcg < args.min_ndcg:
        return 1
    if any(not item["within_budget"] for item in per_topic):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
