# Roadmap

Cairn is built around one constraint: useful retrieval should cost less context
than opening everything. The roadmap is organized by product maturity, not by
implementation history.

## Shipped

- Local Markdown vault with frontmatter schema, profiles, validation, and
  incremental and rebuildable SQLite FTS index.
- Agent-agnostic CLI workflow: search, retrieve, show partial context, capture,
  update, validate, doctor, stats, export, and import.
- Budgeted retrieval for LLM context packets, including passage-level retrieval
  for smaller prompts.
- Deterministic search benchmark with qrels, golden checks, ranking metrics,
  token budgets, and passage-vs-document context reduction.
- BM25 default ranking plus opt-in RRF and `retrieve --ranker auto` fallback.
- Secret-safety checks for validation, retrieval, and export.
- Similar-note detection with fingerprint fallback and `duplicate_candidate` /
  `related` labels.
- Markdown writeback ergonomics through `--body-file`, `--body-stdin`,
  `--append-file`, and `--append-stdin`.
- Standalone GitHub Release binaries, checksums, and quick install scripts for
  Linux, macOS, and Windows.
- Public documentation, example vault, changelog, contribution guide, and GitHub
  Pages overview.

## Now

- Stabilize machine-readable agent workflows with JSON output for retrieval,
  writeback, indexing, validation, and health checks while keeping human text
  output as the default.
- Refactor retrieval around a structured context packet with source provenance,
  budget accounting, ranker metadata, score metadata, and text rendering derived
  from the same model.
- Harden writeback with dry-run output, no-op reasons, and conflict detection
  based on file signatures before agents update shared notes.
- Build a deterministic writeback suite that exercises duplicate prevention,
  note updates, recurring bugs, process notes, access notes, library references,
  and update-vs-create decisions.
- Add benchmark history and comparison data to the public site so regressions in
  retrieval and writeback behavior are visible over time.

## Next

- Add ranking explanation output for search and retrieve, focused on debugging
  and benchmarks rather than confidence claims.
- Add read-only suggestion workflows after similar-note thresholds are measured,
  so agents can propose update-existing vs create-new actions with evidence.
- Surface note freshness and provenance metadata in results without mutating
  Markdown files during read operations.
- Build optional adapters or plugin packages for Codex, Claude, GitHub Copilot,
  OpenCode, Hermes, and other agent harnesses on top of the stable CLI/JSON
  contract.
- Team workflows for reviewing shared vault changes before they become common
  knowledge.
- Better benchmark slices by role and domain, such as engineering, support,
  product, and personal notes.
- More import paths from existing Markdown or Obsidian-style knowledge bases.

## Later

- Optional MCP server or adapter package outside the core CLI.
- Optional embedding backend behind a strict integration boundary, only if
  benchmark slices show lexical retrieval cannot meet target quality.
- Optional watch or notification workflows if real vault usage shows a need for
  long-running change detection.
- UI or TUI for browsing, reviewing, and curating notes.
- Richer analytics for vault health, duplication, stale notes, and coverage gaps.

## Non-goals

- Replacing Markdown as the source of truth.
- Requiring cloud services for local search.
- Making embeddings mandatory for the core workflow.
- Storing credentials, private keys, tokens, or secrets.
- Adding a persistent query cache to the core before benchmarks show SQLite FTS
  query latency is a real bottleneck.
- Presenting uncalibrated ranking scores as confidence.
- Moving MCP servers, watch daemons, or product-specific adapters into the
  dependency-free core.
