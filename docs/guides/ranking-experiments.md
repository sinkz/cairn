# Ranking And Embedding Experiments

This guide defines the bar for changing ApolloKairn retrieval ranking. It is
for issues and pull requests that tune BM25 weights, query variants, RRF,
passage retrieval, or optional embedding adapters.

The default core must stay local-first, dependency-free at runtime, and
deterministic. Embeddings and model calls are optional boundaries, not required
core behavior.

## Current Ranking Knobs

ApolloKairn currently exposes these ranking controls:

| Area | Current control | Location |
| --- | --- | --- |
| Document BM25 | Per-column weights passed to SQLite FTS5 `bm25(docs, ...)` | `src/cairn/indexer.py` |
| Passage BM25 | Per-column weights passed to SQLite FTS5 `bm25(passages, ...)` | `src/cairn/indexer.py` |
| Query variants | Strict, broader, prefix/inflection variants used by RRF | `src/cairn/ranking.py` |
| Tokenizer | FTS5 `unicode61 remove_diacritics 2` for accent-insensitive search | `src/cairn/indexer.py` |
| Glossary expansion | Approved aliases from `glossary.md` for deterministic fallback expansion | `src/cairn/vocabulary.py` |
| RRF | Fixed `k = 60` for fused document and passage runs | `src/cairn/indexer.py` |
| Retrieve fallback | `--ranker auto` tries BM25 first, then RRF | `src/cairn/retriever.py` |

SQLite FTS5's built-in `bm25()` supports weights for indexed columns. Its BM25
`k1` and `b` constants are not configuration knobs in ApolloKairn's current
core path. Changing those would require a custom ranking function or a different
retrieval backend, so it must be treated as architecture work, not a small
weight-tuning issue. See the SQLite FTS5 `bm25()` documentation:
https://sqlite.org/fts5.html#the_bm25_function.

## Required Experiment Runs

Run these before proposing or accepting ranking changes:

```bash
python -m unittest discover
python bench/run_eval.py --quiet --compare-golden bench/golden.json
python bench/run_eval.py --fixture bench/fixtures/vault-large --topics bench/topics-large.jsonl --qrels bench/qrels-large.tsv --quiet --compare-golden bench/golden-large.json
python bench/agent/run_agent_eval.py --dry-run --fixture bench/fixtures/vault-large --tasks bench/agent/tasks-large.jsonl --topics bench/topics-large.jsonl --quiet
python bench/agent/run_agent_eval.py --mock --fixture bench/fixtures/vault-large --tasks bench/agent/tasks-large.jsonl --topics bench/topics-large.jsonl --quiet
python bench/run_grep_baseline.py --quiet --compare-golden bench/grep-golden.json
python bench/run_writeback_eval.py --quiet --compare-golden bench/writeback/golden.json
python bench/run_perf_eval.py --quiet --repeat 1
python bench/publish_metrics.py --output docs/data/benchmarks.json --tests 228
git diff --check
```

For timing-sensitive work, also run the performance suite with more repeats on
the same machine:

```bash
python bench/run_perf_eval.py --quiet --repeat 3
```

## Baseline To Beat

These are the committed baselines as of 2026-06-19:

| Suite | Corpus | Current result |
| --- | --- | --- |
| Retrieval small | 25 Markdown files, 28 topics | `Recall@3 = 1.0`, `MRR@3 = 1.0`, `nDCG@3 = 0.9941` |
| Retrieval large | 304 Markdown files, 80 topics | `Recall@3 = 1.0`, `MRR@3 = 0.9375`, `nDCG@3 = 0.8631` |
| Agent L1 mock | 80 tasks over the large corpus | `context_sufficiency = 1.0`, `abstention_accuracy = 1.0` |
| Grep raw-read baseline | 25 Markdown files, 28 topics | `Recall@20 = 0.7857`, `nDCG@20 = 0.7857`, `tokens = 3988` |
| Writeback | Deterministic create/update/no-op/conflict cases | `decision_accuracy = 1.0` |

The large corpus slices are `exact_error`, `paraphrase`, `cross_doc`,
`role_workflow`, `pt_br`, `noisy_query`, `filtered`, `passage_budget`, and
`no_answer`. The L1 agent mock uses the same slice set.

## Acceptance Criteria

A ranking or embedding experiment is acceptable only when all applicable gates
are satisfied:

| Gate | Required result |
| --- | --- |
| Golden checks | `bench/golden.json`, `bench/golden-large.json`, `bench/grep-golden.json`, and `bench/writeback/golden.json` comparisons pass. |
| Global quality | Small and large retrieval metrics do not regress from the committed baseline unless the issue explicitly accepts the tradeoff. |
| Slice quality | No critical slice regresses by more than `0.01` absolute nDCG or MRR without a written rationale. |
| No-answer behavior | Large `no_answer.false_positive_rate` stays `0.0`; L1 mock `abstention_accuracy` stays `1.0`. |
| Budgets | `budget_compliance_rate` stays `1.0` for retrieval and L1 mock suites. |
| Context cost | `returned_tokens` must not increase by more than 5 percent unless quality improves by at least `0.02` absolute nDCG or the issue documents the tradeoff. |
| Performance | Search/retrieve p95, full-index time, incremental-index time, and index size should not regress by more than 20 percent on the same machine without rationale. |
| Core boundary | `pyproject.toml` keeps runtime `dependencies = []` unless an ADR explicitly changes the architecture. |

Do not treat a higher ranking score as confidence. Ranking metrics show whether
the expected source was returned and ordered well; they do not prove that an
agent answered correctly.

## L1 And L2 Agent Evaluation

`bench/agent/run_agent_eval.py --mock` is a deterministic L1 gate. It validates
the task schema, aggregation, source-path accuracy, expected facts in retrieved
context, abstention tasks, and budget compliance. It measures context
sufficiency, not real model behavior.

Paid or model-backed L2 evaluation should stay outside rigid CI. It can be used
to calibrate whether ranking changes reduce real agent tokens or improve answer
quality. At minimum, record provider, model, temperature, repeat count, token
usage, cost, and the provider-command contract. When the provider uses seeds,
retry policy, or an LLM judge, include those details in the eval report. L2
should compare ApolloKairn against a raw-read or grep baseline on the same task
set.

The runner supports an explicit external-provider contract:

```bash
python bench/agent/run_agent_eval.py --live \
  --provider-command "python path/to/provider.py" \
  --provider-name local-eval \
  --model fixed-model \
  --repeat 5 \
  --output docs/data/agent-evals.json
```

The provider command reads request JSON from stdin. The request includes the
question, retrieved context, source paths, strategy, model, temperature, and
repetition. It does not include `expected_paths` or `expected_facts`. The
provider writes response JSON with `answer`, `cited_paths`, `abstained`,
`tool_calls`, `input_tokens`, `output_tokens`, and `cost_usd`.

## Embedding Experiments

Embedding work is eligible for a plugin or adapter issue only when it keeps the
core contract intact:

- disabled by default and not required for install, indexing, search, retrieve,
  writeback, or tests;
- no note bodies sent to network services unless the user explicitly opts in;
- local index remains rebuildable from Markdown source of truth;
- lexical BM25/RRF fallback remains available and covered by deterministic
  tests;
- model name, dimension count, storage size, indexing time, query latency, and
  refresh behavior are reported;
- improvement is concentrated in slices that lexical retrieval should struggle
  with, such as `paraphrase`, `cross_doc`, `pt_br`, or `role_workflow`;
- exact-error, filtered, budget, and no-answer slices do not regress.

## Issue Template For Experiments

Every ranking experiment issue should include:

```text
Hypothesis:
Changed knobs:
Expected improving slices:
Expected risk slices:
Commands run:
Before/after global metrics:
Before/after slice metrics:
Returned token delta:
Performance delta:
L1 mock result:
Decision:
```

If the issue proposes custom BM25 `k1` or `b`, a custom ranker, or embeddings in
the core package, it needs an architecture decision first.
