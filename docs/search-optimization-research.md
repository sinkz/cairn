# Search Optimization Research Notes

Date: 2026-06-17

This document consolidates two independent researcher-agent reports. The agents
were instructed to work with MIT-level rigor: review information retrieval
literature, search algorithms, proof-of-concept approaches, and deterministic
evaluation strategies for Cairn.

## Problem

Cairn should help humans and agents reuse a Markdown knowledge vault without
opening everything. The search system must maximize useful recall while keeping
LLM context small, deterministic, local-first, and easy to audit.

## External References

- NIST Cranfield/TREC evaluation background: https://www.nist.gov/publications/evolution-cranfield
- NIST paper on IR evaluation philosophy: https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=151546
- Reciprocal Rank Fusion, Cormack, Clarke, Buettcher, SIGIR 2009: https://dl.acm.org/doi/10.1145/1571941.1572114
- SQLite FTS5 official documentation: https://sqlite.org/fts5.html
- Lost in the Middle, Liu et al., TACL 2024: https://arxiv.org/abs/2307.03172

## Researcher A: Retrieval Algorithms

Main recommendations:

- Keep SQLite FTS5/BM25 as the core retrieval engine.
- Add explicit tokenizer configuration for accent-insensitive Unicode search.
- Add query variants and Reciprocal Rank Fusion only after benchmark coverage is
  in place.
- Move from document-only retrieval to passage retrieval by heading or paragraph.
- Add duplicate detection in layers: lexical score first, lightweight fingerprints
  later, embeddings only as an optional integration.
- Avoid making embeddings mandatory until deterministic benchmarks prove that
  they improve recall or cost for the target corpus.

Reasoning:

Lexical search is deterministic, cheap, offline, inspectable, and good enough for
many second-brain queries where users remember concrete symptoms, filenames,
errors, products, or process terms. RRF is attractive because it can combine
several cheap lexical runs without training a model. Passage retrieval matters
because LLM performance can degrade when too much irrelevant context is included.

## Researcher B: Evaluation And Benchmarks

Main recommendations:

- Use a Cranfield/TREC-style harness: fixed corpus, fixed topics, fixed qrels,
  and comparable run output.
- Measure search quality and token cost together.
- Include regression metrics that catch ranking churn, budget overflow, and
  recall loss.
- Add fixture scenarios for engineering, product, support, PT-BR accents,
  metadata filters, stale index behavior, duplicates, and budgeted retrieval.

Recommended metrics:

- `Recall@k`: did the relevant document appear in the returned set?
- `MRR@k`: how early did the first relevant result appear?
- `nDCG@k`: did the ranking place higher-relevance items near the top?
- `returned_tokens`: approximate tokens sent to the LLM.
- `context_reduction`: avoided context compared with opening the full corpus.
- `within_budget`: whether retrieval stayed under the requested budget.

## Debate And Consensus

The main disagreement was sequence. One side favored ranking upgrades first
because RRF and passage retrieval are likely improvements. The other side argued
that without a deterministic evaluation harness, those changes could silently
improve one query while breaking another.

Consensus:

1. Build the benchmark before larger ranking changes.
2. Keep the default search lexical and local-first.
3. Apply low-risk tokenizer improvements now.
4. Introduce RRF behind measured experiments, not as an untested default.
5. Introduce passage retrieval next because it directly reduces LLM context.
6. Keep embeddings optional until they beat lexical search on real Cairn tasks.

## Implemented From This Round

- Added `bench/topics.jsonl` with fixed benchmark queries.
- Added `bench/qrels.tsv` with relevance judgments.
- Added `bench/fixtures/vault` as a deterministic mini-corpus.
- Added `bench/run_eval.py` to compute `Recall@k`, `MRR@k`, `nDCG@k`, returned
  token cost, and context reduction.
- Added CI execution for the deterministic benchmark.
- Added explicit FTS5 `unicode61 remove_diacritics 2` tokenizer configuration.
- Added a PT-BR accent regression test.
- Expanded the benchmark to harder fixtures for exact errors, filters, current
  decisions, near duplicates, hotfix rollback, and synonym/alias retrieval.
- Added `bench/golden.json` and CI comparison to catch ranking regressions on
  stable critical queries.
- Added Markdown passage splitting, passage FTS indexing, and
  `cairn retrieve --mode passages`.
- Added benchmark `compare_mode` support and aggregate comparison metrics to
  compare token usage between document and passage retrieval on the same topic.
- Added an opt-in document `rrf` ranker and benchmark `ranker` /
  `compare_ranker` support to measure it against the default `bm25` baseline.
- Added benchmark `category` labels and expanded coverage for alias-heavy
  queries, multilingual retrieval, RRF with filters, role workflows, access
  processes, and library decisions.
- Added lightweight SimHash-style fingerprint fallback for `cairn similar` so
  duplicate checks can find near matches even when strict lexical search misses.
- Added an agent workflow test that captures, indexes, searches, retrieves,
  checks similarity, and updates a note through the CLI.

Current benchmark result:

```text
topics: 24
limit: 3
mean_recall_at_3: 1.0
mean_mrr_at_3: 1.0
mean_ndcg_at_3: 0.9931
full_context_tokens: 69960
returned_tokens: 5482
context_reduction: 0.9216
comparison_topics: 5
comparison_candidate_tokens: 521
comparison_baseline_tokens: 1126
comparison_token_reduction: 0.5373
```

Regression gates:

```text
Recall@3 >= 0.90
MRR@3 >= 0.80
nDCG@3 >= 0.80
all topics within token budget
golden critical-query prefixes unchanged
```

The benchmark is intentionally no longer perfect. A generic deploy query now has
multiple plausible matches, so aggregate metrics and golden checks are used
together: metrics allow legitimate ranking improvements, while golden checks
protect critical exact cases from silent regressions.

The passage-mode benchmark topics cover deploy resolution, JWT clock skew,
support escalation steps, hotfix rollback steps, and database pool exhaustion
resolution. Together they return 521 candidate tokens versus 1126 document-mode
baseline tokens, a 53.73% reduction while preserving `Recall@3 = 1.0`.

The first RRF benchmark topic covers a noisy query with one extra unrelated term:
`deploy token rotation kubernetes secret`. The default `bm25` baseline returns no
documents, while opt-in `rrf` returns `knowledge/deploy-403.md` at rank 1 and
preserves `Recall@3 = 1.0` for that topic.

The categorized benchmark now also guards alias lookup, PT-BR accent-insensitive
retrieval, RRF combined with filters, PO/support backlog workflows, production
access processes, and library/formatting decisions.

## Next Experiments

### Passage Retrieval

Index Markdown sections or paragraphs as retrievable units with:

- document path;
- heading path;
- line start and end;
- section text;
- inherited frontmatter metadata.

Success criteria:

- maintain `Recall@3 >= 1.0` on current fixtures;
- reduce `returned_tokens` by at least 20% versus document-level retrieval;
- preserve stable `show --section` and `show --lines` references.

Status: initial heading-based passage retrieval and aggregate passage-vs-document
benchmark coverage are implemented. Next work should add paragraph-level
splitting only if heading-level passages are too coarse.

### RRF Query Variants

Run multiple cheap lexical searches and merge them with Reciprocal Rank Fusion:

- quoted strict query;
- quoted OR query;
- safe prefix/inflection query for longer alphabetic terms;
- metadata, aliases, systems, and signals through the existing FTS content
  fields.

Success criteria:

- no recall regression on current fixtures;
- improved MRR on synonym and alias-heavy fixtures;
- minimal latency increase on local vaults.

Status: opt-in RRF is implemented for document search/retrieval and passage
retrieval. It fuses strict, broader OR, and conservative prefix/inflection
lexical runs, leaves the default `bm25` behavior unchanged, and is measured
against `compare_ranker: bm25` in the deterministic benchmark. Document and
passage fixtures cover noisy extra-term queries and inflection-only queries
where the strict ranker returns no result.

### Duplicate Fingerprints

Add lightweight fingerprints for duplicate checks:

- normalized title tokens;
- Jaccard overlap over title/description/signals;
- optional SimHash-style fingerprint for note bodies.

Success criteria:

- lower duplicate creation in fixture scenarios;
- no dependency required in core runtime.

Status: initial fingerprint-backed duplicate detection is implemented in
`cairn similar`. It keeps indexed lexical search as the first source of
candidates, then scans local Markdown notes with a lightweight SimHash-style
fingerprint to catch near duplicates with extra terms. The implementation stays
stdlib-only and respects type, tag, and system filters.

### Optional Embeddings

Treat embeddings as a plugin boundary:

- never required for local-first core operation;
- disabled by default;
- benchmarked against lexical and RRF modes;
- must report storage size, refresh cost, and token impact.
