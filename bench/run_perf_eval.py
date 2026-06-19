from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Callable, Sequence


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "bench"))

from cairn.indexer import rebuild_index, search, search_passages, sync_index
from cairn.retriever import retrieve_packet
from run_eval import Topic, load_topics


def _ms(call: Callable[[], object]) -> tuple[float, object]:
    started = perf_counter()
    result = call()
    return round((perf_counter() - started) * 1000, 4), result


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((len(ordered) - 1) * percentile)))
    return round(ordered[index], 4)


def _summary(values: Sequence[float]) -> dict[str, float | int]:
    if not values:
        return {"samples": 0, "min": 0.0, "p50": 0.0, "p95": 0.0, "max": 0.0}
    return {
        "samples": len(values),
        "min": round(min(values), 4),
        "p50": round(median(values), 4),
        "p95": _percentile(values, 0.95),
        "max": round(max(values), 4),
    }


def _run_search(root: Path, topic: Topic, limit: int) -> object:
    if topic.mode == "passages":
        return search_passages(
            root,
            topic.query,
            limit=topic.limit or limit,
            type_filter=topic.type_filter,
            tag_filters=topic.tag_filters,
            system_filters=topic.system_filters,
            ranker=topic.ranker,
        )
    return search(
        root,
        topic.query,
        limit=topic.limit or limit,
        type_filter=topic.type_filter,
        tag_filters=topic.tag_filters,
        system_filters=topic.system_filters,
        ranker=topic.ranker,
    )


def _run_retrieve(root: Path, topic: Topic, limit: int) -> object:
    return retrieve_packet(
        root,
        topic.query,
        limit=topic.limit or limit,
        budget_tokens=topic.budget,
        mode=topic.mode,
        type_filter=topic.type_filter,
        tag_filters=topic.tag_filters,
        system_filters=topic.system_filters,
        ranker=topic.ranker,
    )


def _touch_one_note(root: Path) -> None:
    for path in sorted(root.rglob("*.md")):
        if ".cairn" in path.relative_to(root).parts:
            continue
        if path.name in {"AGENTS.md", "SCHEMA.md", "index.md", "log.md"}:
            continue
        path.write_text(path.read_text(encoding="utf-8") + "\n<!-- perf incremental touch -->\n", encoding="utf-8", newline="\n")
        return
    raise FileNotFoundError("no benchmark note found to touch")


def evaluate(root: Path, topics: Sequence[Topic], repeat: int, limit: int) -> dict[str, object]:
    full_index_ms, _ = _ms(lambda: rebuild_index(root))
    search_samples: list[float] = []
    retrieve_samples: list[float] = []
    for _ in range(repeat):
        for topic in topics:
            elapsed, _ = _ms(lambda topic=topic: _run_search(root, topic, limit))
            search_samples.append(elapsed)
            elapsed, _ = _ms(lambda topic=topic: _run_retrieve(root, topic, limit))
            retrieve_samples.append(elapsed)

    _touch_one_note(root)
    incremental_ms, stats = _ms(lambda: sync_index(root))
    db_path = root / ".cairn" / "index.db"
    return {
        "suite": "performance",
        "topics": len(topics),
        "repeat": repeat,
        "limit": limit,
        "full_index_ms": full_index_ms,
        "incremental_index_ms": incremental_ms,
        "incremental_index": {
            "updated": stats.updated,
            "removed": stats.removed,
            "skipped": stats.skipped,
        },
        "index_db_bytes": db_path.stat().st_size if db_path.exists() else 0,
        "search_ms": _summary(search_samples),
        "retrieve_ms": _summary(retrieve_samples),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local performance benchmark for search/retrieve/index.")
    parser.add_argument("--fixture", default=str(ROOT / "bench" / "fixtures" / "vault-large"))
    parser.add_argument("--topics", default=str(ROOT / "bench" / "topics-large.jsonl"))
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if args.repeat <= 0:
        print("perf eval error: repeat must be positive", file=sys.stderr)
        return 2
    if args.limit <= 0:
        print("perf eval error: limit must be positive", file=sys.stderr)
        return 2

    try:
        topics = load_topics(Path(args.topics))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"perf eval error: {exc}", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "vault"
        shutil.copytree(Path(args.fixture), root)
        payload = evaluate(root, topics, args.repeat, args.limit)

    if args.quiet:
        print(
            "perf ok "
            f"topics={payload['topics']} "
            f"search_p50_ms={payload['search_ms']['p50']} "
            f"retrieve_p50_ms={payload['retrieve_ms']['p50']} "
            f"full_index_ms={payload['full_index_ms']} "
            f"db_bytes={payload['index_db_bytes']}"
        )
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
