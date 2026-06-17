# Cairn Search Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve Cairn retrieval quality and reduce LLM context cost with deterministic evidence before changing defaults.

**Architecture:** Keep SQLite FTS5/BM25 as the local-first core. Add a stronger benchmark harness first, then passage-level retrieval, then measured RRF query variants, then stronger duplicate detection. Embeddings stay out of core until the lexical stack has measured limits.

**Tech Stack:** Python 3.11+, standard library only, argparse, sqlite3 FTS5, unittest, Markdown fixtures, JSONL topics, TSV qrels.

---

## Opinion On The Research

The researchers converged on the right strategy: benchmark first, optimize second.
The current benchmark is useful but too easy: every query has a single obvious
answer and current metrics are saturated at `1.0`. That means it is good as a CI
smoke gate, but not enough to prove future ranking changes.

The next implementation should not start with embeddings. Cairn's daily queries
will often contain concrete identifiers such as error codes, command names,
file paths, systems, tags, symptoms, and support/process terms. BM25 plus better
context packaging should remain the default until a benchmark proves otherwise.

## File Structure

- Modify `bench/run_eval.py`: add richer metrics, golden comparison, filter cases, latency, and per-query token accounting.
- Modify `bench/topics.jsonl`: add query metadata such as `mode`, `type`, `tag`, `system`, `limit`, and `budget`.
- Modify `bench/qrels.tsv`: add more qrels with graded relevance.
- Modify `bench/fixtures/vault/**`: add harder fixtures for synonym traps, exact identifiers, stale decisions, duplicates, and PT-BR.
- Create `src/cairn/passages.py`: split Markdown into stable passages with path, heading, line range, text, and inherited metadata.
- Modify `src/cairn/indexer.py`: index passage rows and expose passage search while preserving document search.
- Modify `src/cairn/retriever.py`: support passage-based retrieval packets.
- Modify `src/cairn/cli.py`: expose retrieval/search mode flags.
- Create `src/cairn/ranking.py`: implement query variants and Reciprocal Rank Fusion.
- Modify `src/cairn/similar.py`: add fingerprint-backed duplicate suggestions.
- Create `src/cairn/fingerprints.py`: normalized title, Jaccard tokens, and SimHash-style body fingerprint.
- Add or modify `tests/test_passages.py`, `tests/test_retriever.py`, `tests/test_indexer.py`, `tests/test_ranking.py`, `tests/test_similar.py`, and `tests/test_bench.py`.
- Update `docs/search-optimization-research.md`, `docs/guides/usage.md`, and `docs/guides/usage.pt-BR.md` after commands stabilize.

## Task 1: Harden The Deterministic Benchmark

**Files:**
- Modify: `bench/run_eval.py`
- Modify: `bench/topics.jsonl`
- Modify: `bench/qrels.tsv`
- Modify: `bench/fixtures/vault/**`
- Create: `tests/test_bench.py`

- [ ] **Step 1: Add benchmark cases before changing search**

Add fixtures for these cases:

```text
q_exact_001 -> query "ERR_DB_POOL_EXHAUSTED checkout" should rank the exact error note first.
q_syn_001 -> query "login token refresh" should find a note whose body says "session cookie rotation".
q_filter_001 -> query "deploy 403" with system "mobile" must not return the CI deploy note.
q_decision_current_001 -> current ADR must outrank superseded ADR.
q_duplicate_001 -> consolidated note must outrank near-duplicate daily notes.
q_budget_001 -> passage mode later must return fewer tokens than document mode.
```

- [ ] **Step 2: Write failing tests for metric behavior**

Add `tests/test_bench.py`:

```python
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BenchTests(unittest.TestCase):
    def test_benchmark_outputs_quality_and_token_metrics(self) -> None:
        result = subprocess.run(
            [sys.executable, "bench/run_eval.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("mean_recall_at_k", payload)
        self.assertIn("mean_mrr_at_k", payload)
        self.assertIn("mean_ndcg_at_k", payload)
        self.assertIn("returned_tokens", payload)
        self.assertIn("context_reduction", payload)
        self.assertGreaterEqual(payload["topics"], 10)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the failing test**

Run:

```bash
python -m unittest tests.test_bench -v
```

Expected before fixtures are expanded:

```text
FAIL: 5 not greater than or equal to 10
```

- [ ] **Step 4: Expand `bench/run_eval.py` without adding dependencies**

Add support for topic filters:

```json
{"id":"q_filter_001","query":"deploy 403","system":["mobile"],"budget":600,"limit":3}
```

The evaluator should pass `type`, `tag`, and `system` values into `search()` and
`retrieve()` when present.

- [ ] **Step 5: Add golden comparison**

Add a `--write-golden PATH` and `--compare-golden PATH` option. The golden file
stores each query ID and its ranked document IDs:

```json
{
  "q1": ["knowledge/deploy-403.md"],
  "q_exact_001": ["knowledge/db-pool-exhausted.md"]
}
```

Comparison fails when the first relevant document drops out of top 3.

- [ ] **Step 6: Verify benchmark**

Run:

```bash
python -m unittest tests.test_bench -v
python bench/run_eval.py --quiet
python -m unittest discover -v
```

Expected:

```text
OK
bench ok recall@3=... mrr@3=... ndcg@3=...
```

Do not require all metrics to stay at `1.0` after harder fixtures. Initial gates:

```text
Recall@3 >= 0.90
MRR@3 >= 0.80
nDCG@3 >= 0.80
every query within budget
```

## Task 2: Passage Splitting

**Files:**
- Create: `src/cairn/passages.py`
- Create: `tests/test_passages.py`

- [ ] **Step 1: Write failing passage unit tests**

Add `tests/test_passages.py`:

```python
from __future__ import annotations

import unittest

from cairn.passages import split_passages


class PassageTests(unittest.TestCase):
    def test_split_passages_uses_heading_and_line_ranges(self) -> None:
        text = (
            "---\n"
            "type: Runbook\n"
            "title: Deploy 403\n"
            "description: Fix deploy.\n"
            "tags: [deploy]\n"
            "timestamp: 2026-06-17T10:00:00Z\n"
            "---\n\n"
            "# Context\n\n"
            "Deploy fails with HTTP 403.\n\n"
            "# Resolution\n\n"
            "Rotate the CI token.\n"
        )

        passages = split_passages("knowledge/deploy-403.md", text)

        self.assertEqual(passages[0].path, "knowledge/deploy-403.md")
        self.assertEqual(passages[0].heading, "Context")
        self.assertIn("HTTP 403", passages[0].text)
        self.assertGreaterEqual(passages[0].start_line, 1)
        self.assertGreaterEqual(passages[0].end_line, passages[0].start_line)
        self.assertEqual(passages[1].heading, "Resolution")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run failing test**

Run:

```bash
python -m unittest tests.test_passages -v
```

Expected:

```text
ModuleNotFoundError: No module named 'cairn.passages'
```

- [ ] **Step 3: Implement `src/cairn/passages.py`**

Add:

```python
from __future__ import annotations

import re
from dataclasses import dataclass

from cairn.frontmatter import parse_document


_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class Passage:
    path: str
    heading: str
    start_line: int
    end_line: int
    text: str


def split_passages(path: str, document: str) -> list[Passage]:
    parsed = parse_document(document)
    body_lines = parsed.body.splitlines()
    frontmatter_lines = len(document.split("---", 2)[0].splitlines()) + 2
    passages: list[Passage] = []
    current_heading = "Document"
    current_start = 1
    current_lines: list[str] = []

    def flush(end_line: int) -> None:
        text = "\n".join(line for line in current_lines).strip()
        if text:
            passages.append(
                Passage(
                    path=path,
                    heading=current_heading,
                    start_line=current_start + frontmatter_lines,
                    end_line=end_line + frontmatter_lines,
                    text=text,
                )
            )

    for idx, line in enumerate(body_lines, start=1):
        match = _HEADING.match(line)
        if match:
            flush(idx - 1)
            current_heading = match.group(2).strip()
            current_start = idx
            current_lines = [line]
            continue
        current_lines.append(line)
    flush(len(body_lines))
    return passages
```

- [ ] **Step 4: Verify passage tests**

Run:

```bash
python -m unittest tests.test_passages -v
```

Expected:

```text
OK
```

## Task 3: Passage Index And Search

**Files:**
- Modify: `src/cairn/indexer.py`
- Modify: `tests/test_indexer.py`

- [ ] **Step 1: Write failing tests for passage search**

Add to `tests/test_indexer.py`:

```python
def test_search_passages_returns_line_range_and_heading(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        init_vault(root, profile_name="engineering")
        write_concept(
            root,
            "deploy-403.md",
            (
                "type: Runbook",
                "title: Deploy 403",
                "description: Fix deploy failures.",
                "tags: [deploy, bug]",
                "timestamp: 2026-06-17T10:00:00Z",
            ),
            "# Context\n\nNoise.\n\n# Resolution\n\nRotate the CI token.\n",
        )
        rebuild_index(root)

        from cairn.indexer import search_passages

        results = search_passages(root, "rotate ci token", limit=3)

        self.assertEqual(results[0].path, "knowledge/deploy-403.md")
        self.assertEqual(results[0].heading, "Resolution")
        self.assertGreater(results[0].end_line, results[0].start_line)
```

- [ ] **Step 2: Run failing test**

Run:

```bash
python -m unittest tests.test_indexer.IndexerTests.test_search_passages_returns_line_range_and_heading -v
```

Expected:

```text
ImportError: cannot import name 'search_passages'
```

- [ ] **Step 3: Extend index schema**

In `src/cairn/indexer.py`, add `PassageSearchResult` and a `passages` FTS table:

```python
@dataclass(frozen=True)
class PassageSearchResult:
    path: str
    title: str
    type: str
    tags: list[str]
    heading: str
    start_line: int
    end_line: int
    score: float
    snippet: str
```

Add a new virtual table with columns:

```text
path, type, title, tags, systems, heading, line_range, text, content
```

When each document is upserted, call `split_passages(rel, full_text)` and insert
one row per passage.

- [ ] **Step 4: Implement `search_passages`**

`search_passages` should mirror `search`, use the same filters, and return
passage snippets from the passage `text` column. It must keep deterministic
ordering by score and path when possible.

- [ ] **Step 5: Verify passage index**

Run:

```bash
python -m unittest tests.test_indexer -v
python -m unittest discover -v
```

Expected:

```text
OK
```

## Task 4: Passage-Based Retrieval

**Files:**
- Modify: `src/cairn/retriever.py`
- Modify: `src/cairn/cli.py`
- Modify: `tests/test_retriever.py`
- Modify: `bench/run_eval.py`

- [ ] **Step 1: Write failing retrieval test**

Add to `tests/test_retriever.py`:

```python
def test_cli_retrieve_passages_uses_less_context_than_documents(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        init_vault(root, profile_name="engineering")
        write_concept(
            root,
            "large.md",
            (
                "type: Runbook",
                "title: Large deploy note",
                "description: Deploy troubleshooting.",
                "tags: [deploy]",
                "timestamp: 2026-06-17T10:00:00Z",
            ),
            "# Context\n\n" + ("noise " * 200) + "\n\n# Resolution\n\nrotate token needle\n",
        )
        run_cairn(root, "index", "--rebuild")

        doc = run_cairn(root, "retrieve", "rotate token needle", "--budget", "800")
        passage = run_cairn(root, "retrieve", "rotate token needle", "--budget", "800", "--mode", "passages")

        self.assertEqual(doc.returncode, 0, doc.stderr)
        self.assertEqual(passage.returncode, 0, passage.stderr)
        self.assertIn("heading: Resolution", passage.stdout)
        self.assertLess(len(passage.stdout), len(doc.stdout))
```

- [ ] **Step 2: Run failing test**

Run:

```bash
python -m unittest tests.test_retriever.RetrieverTests.test_cli_retrieve_passages_uses_less_context_than_documents -v
```

Expected:

```text
error: unrecognized arguments: --mode passages
```

- [ ] **Step 3: Add CLI mode**

In `src/cairn/cli.py`, add:

```python
retrieve_cmd.add_argument("--mode", choices=["documents", "passages"], default="documents")
```

Pass `mode=args.mode` into `retrieve()`.

- [ ] **Step 4: Implement retriever mode**

In `src/cairn/retriever.py`, extend signature:

```python
def retrieve(..., mode: str = "documents") -> str:
```

When `mode == "passages"`, call `search_passages()` and render:

```text
path: knowledge/deploy-403.md
title: Deploy 403
type: Runbook
tags: deploy, bug
heading: Resolution
lines: 14:18
snippet: ...
content:
...
```

- [ ] **Step 5: Add benchmark comparison**

Modify `bench/run_eval.py` so a topic can set:

```json
{"id":"q_budget_001","query":"rotate token needle","mode":"passages","budget":400}
```

Store `mode` in per-topic output.

- [ ] **Step 6: Verify token reduction**

Run:

```bash
python -m unittest tests.test_retriever -v
python bench/run_eval.py --quiet
python -m unittest discover -v
```

Success criteria:

```text
passage retrieval keeps Recall@3 above gate
returned_tokens drops by at least 20% on q_budget_001
all topics stay within budget
```

## Task 5: Reciprocal Rank Fusion Query Variants

**Files:**
- Create: `src/cairn/ranking.py`
- Modify: `src/cairn/indexer.py`
- Modify: `src/cairn/cli.py`
- Create: `tests/test_ranking.py`
- Modify: `tests/test_indexer.py`

- [ ] **Step 1: Write deterministic RRF test**

Add `tests/test_ranking.py`:

```python
from __future__ import annotations

import unittest

from cairn.ranking import rrf_merge


class RankingTests(unittest.TestCase):
    def test_rrf_merge_is_deterministic(self) -> None:
        runs = [
            ["a.md", "b.md", "c.md"],
            ["b.md", "a.md", "d.md"],
        ]

        merged = rrf_merge(runs, k=60)

        self.assertEqual(merged[0], "a.md")
        self.assertEqual(merged[1], "b.md")
        self.assertEqual(merged[2], "c.md")
        self.assertEqual(merged[3], "d.md")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run failing test**

Run:

```bash
python -m unittest tests.test_ranking -v
```

Expected:

```text
ModuleNotFoundError: No module named 'cairn.ranking'
```

- [ ] **Step 3: Implement `rrf_merge`**

Add `src/cairn/ranking.py`:

```python
from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence


def rrf_merge(runs: Sequence[Sequence[str]], k: int = 60) -> list[str]:
    scores: dict[str, float] = defaultdict(float)
    first_seen: dict[str, int] = {}
    counter = 0
    for run in runs:
        for rank, doc_id in enumerate(run, start=1):
            if doc_id not in first_seen:
                first_seen[doc_id] = counter
                counter += 1
            scores[doc_id] += 1.0 / (k + rank)
    return sorted(scores, key=lambda doc_id: (-scores[doc_id], first_seen[doc_id], doc_id))
```

- [ ] **Step 4: Add search modes**

Add CLI flag:

```python
search_cmd.add_argument("--mode", choices=["strict", "balanced"], default="strict")
retrieve_cmd.add_argument("--search-mode", choices=["strict", "balanced"], default="strict")
```

`strict` preserves current behavior. `balanced` runs multiple FTS query variants
and merges IDs with RRF:

```text
variant 1: current quoted AND query
variant 2: OR query for recall
variant 3: metadata-heavy query over title/description/tags/aliases/signals
```

- [ ] **Step 5: Verify no regression**

Run:

```bash
python -m unittest tests.test_ranking -v
python -m unittest tests.test_indexer -v
python bench/run_eval.py --quiet
```

Success criteria:

```text
strict mode benchmark unchanged
balanced mode improves synonym fixture or ties it
balanced mode does not reduce Recall@3 below gate
```

## Task 6: Duplicate Fingerprints

**Files:**
- Create: `src/cairn/fingerprints.py`
- Modify: `src/cairn/similar.py`
- Modify: `tests/test_similar.py`

- [ ] **Step 1: Write fingerprint tests**

Add to `tests/test_similar.py`:

```python
def test_similar_detects_near_duplicate_title_and_body(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        init_vault(root, profile_name="engineering")
        write_concept(
            root,
            "deploy-403.md",
            (
                "type: Runbook",
                "title: Deploy 403 after token rotation",
                "description: Fix stale CI authorization.",
                "tags: [deploy, bug]",
                "timestamp: 2026-06-17T10:00:00Z",
            ),
            "# Context\n\nRotate the CI token after HTTP 403 deploy failure.\n",
        )
        rebuild_index(root)

        result = run_cairn(root, "similar", "deploy forbidden after token rotation", "--json")

        payload = json.loads(result.stdout)
        self.assertEqual(payload[0]["path"], "knowledge/deploy-403.md")
        self.assertGreaterEqual(payload[0]["similarity"], 0.5)
```

- [ ] **Step 2: Implement fingerprints**

Add functions:

```python
def normalized_tokens(text: str) -> set[str]
def jaccard(left: set[str], right: set[str]) -> float
def simhash64(text: str) -> int
def hamming_distance(left: int, right: int) -> int
```

Use these only as signals in `similar`; do not block note creation automatically.

- [ ] **Step 3: Verify duplicate behavior**

Run:

```bash
python -m unittest tests.test_similar -v
python -m unittest discover -v
```

Success criteria:

```text
near duplicates rank high
related but different docs do not receive a high duplicate score
similar output remains JSON-compatible
```

## Task 7: Documentation And CI Gates

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `docs/guides/usage.md`
- Modify: `docs/guides/usage.pt-BR.md`
- Modify: `docs/search-optimization-research.md`
- Modify: `ROADMAP.md`

- [ ] **Step 1: Update docs after commands are stable**

Document:

```bash
cairn retrieve "query" --mode passages --budget 600
cairn search "query" --mode balanced --json
python bench/run_eval.py --quiet
```

- [ ] **Step 2: Keep CI running unit tests and benchmark**

CI must continue running:

```bash
python -m unittest discover -v
python bench/run_eval.py --quiet
```

- [ ] **Step 3: Verify full story**

Run locally:

```bash
python -m unittest discover -v
python bench/run_eval.py
python -m cairn validate --path examples/engineering-vault
python -m cairn validate --path bench/fixtures/vault
git diff --check
```

Expected:

```text
unit tests OK
benchmark exits 0 and prints metrics
vault validations exit 0
git diff --check exits 0
```

## Implementation Order

1. Harden benchmark.
2. Implement passage splitting.
3. Index and search passages.
4. Add passage retrieval mode.
5. Add RRF balanced mode.
6. Add duplicate fingerprints.
7. Update docs and CI gates.

## Stop Conditions

Abort or redesign the current step if:

- `Recall@3` drops below `0.90`;
- `MRR@3` drops below `0.80`;
- `nDCG@3` drops below `0.80`;
- any benchmark topic exceeds its token budget;
- passage retrieval fails to reduce token output on budget fixtures;
- a search optimization requires a non-stdlib dependency in core.

## Commit Strategy

Commit after each task:

```bash
git commit -m "Expand search benchmark fixtures"
git commit -m "Add passage splitting"
git commit -m "Index passage search"
git commit -m "Add passage retrieval mode"
git commit -m "Add balanced RRF search mode"
git commit -m "Improve duplicate detection"
git commit -m "Document search optimization workflow"
```
