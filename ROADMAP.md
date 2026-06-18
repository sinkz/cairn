# Roadmap

ApolloKairn is built around one constraint: useful retrieval should cost less context
than opening everything. The roadmap is organized by product maturity, not by
implementation history.

## Shipped

- Local Markdown vault with frontmatter schema, profiles, validation, and
  incremental and rebuildable SQLite FTS index.
- Agent-agnostic CLI workflow: search, retrieve, show partial context, capture,
  update, validate, doctor, stats, export, and import.
- Machine-readable `--json` output for all operational commands, including
  vault setup, archive import/export, guide generation, writeback, validation,
  retrieval, and glossary management.
- Local vault registry with named vaults, one active vault, `--vault` command
  resolution, and JSON-friendly discovery for agents working from other
  repositories.
- Budgeted retrieval for LLM context packets, including passage-level retrieval
  for smaller prompts.
- Structured retrieval packets with source provenance, budget accounting,
  ranker metadata, score metadata, and text rendering derived from the same
  model.
- Deterministic search benchmark with qrels, golden checks, ranking metrics,
  token budgets, and passage-vs-document context reduction.
- Deterministic writeback benchmark with update-vs-create, no-op, conflict,
  duplicate-avoidance, and golden decision checks.
- Public benchmark JSON and GitHub Pages cards for retrieval and writeback
  metrics, including current values and history.
- BM25 default ranking plus opt-in RRF and `retrieve --ranker auto` fallback.
- Top-level deterministic glossary with `apollokairn vocab`, approved aliases, and
  benchmark coverage for synonym gaps such as `k8s`/`kubernetes`.
- Ranking explanation output for search and retrieve, including matched
  fields/terms and glossary alias diagnostics without confidence claims.
- Secret-safety checks for validation, retrieval, and export.
- Similar-note detection with fingerprint fallback and `duplicate_candidate` /
  `related` labels.
- Markdown writeback ergonomics through `--body-file`, `--body-stdin`,
  `--append-file`, and `--append-stdin`.
- Pre-write policy validation for `capture`/`add` and `update`: new notes are
  checked against `SCHEMA.md`, and new content is scanned for common
  secret-like values before files are written.
- Writeback dry-run output, no-op reasons, and stale-write conflict detection
  based on file signatures before agents update shared notes.
- Disciplined generated agent guides for `AGENTS.md`, `CODEX.md`, `CLAUDE.md`,
  `OPENCODE.md`, `HERMES.md`, and GitHub Copilot instructions, including JSON
  search, passage retrieval, glossary guidance, schema-compatible writes,
  multi-line body handling, and post-write validation/indexing.
- Standalone GitHub Release binaries, checksums, and quick install scripts for
  Linux, macOS, and Windows.
- Opt-in local usage metrics with redacted JSONL events and static vault reports
  for pilot evaluation.
- Public documentation, example vault, changelog, contribution guide, and GitHub
  Pages overview.

## Now

- Add more benchmark slices for explanation quality and multi-role vaults.
- Prototype optional plugin or MCP adapter packages outside the dependency-free
  core.
- Design read-only suggestion workflows after similar-note thresholds are
  measured, so agents can propose update-existing vs create-new actions with
  evidence.

## Next

- Surface note freshness and provenance metadata in results without mutating
  Markdown files during read operations.
- Build richer optional plugin packages for Codex, Claude, GitHub Copilot,
  OpenCode, Hermes, and other agent harnesses on top of the stable CLI/JSON
  contract.
- Team workflows for reviewing shared vault changes before they become common
  knowledge.
- Better benchmark slices by role and domain, such as engineering, support,
  product, personal notes, and multi-agent writeback behavior.
- More import paths from existing Markdown or Obsidian-style knowledge bases.

## Later

- Optional MCP server or adapter package outside the core CLI.
- Optional embedding backend behind a strict integration boundary, only if
  benchmark slices show lexical retrieval cannot meet target quality.
- Optional watch or notification workflows if real vault usage shows a need for
  long-running change detection.
- UI or TUI for browsing, reviewing, and curating notes.
- Deeper analytics for vault health, duplication, stale notes, explicit
  relevance feedback, and coverage gaps.

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
