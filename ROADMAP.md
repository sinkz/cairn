# Roadmap

Cairn is built around one constraint: useful retrieval should cost less context
than opening everything. The roadmap prioritizes measurable search quality,
local-first workflows, and agent interoperability.

## Current Focus

- Categorized deterministic search benchmarks with fixed fixtures, queries, qrels, golden checks, and token metrics.
- Passage-based retrieval with measurable context reduction.
- Experimental RRF ranking for documents and passages measured against BM25 without changing the default.
- Secret-safety checks for validation, retrieval, and export.
- Fingerprint-backed duplicate detection beyond exact lexical overlap.
- More robust agent writeback flows for capturing solved problems and updating existing notes.
- Capture/update ergonomics for Markdown from file/stdin and safer path handling.
- Retrieve auto-ranker fallback that tries BM25 first and RRF only when needed.
- Public documentation, examples, and contribution workflow.

## Next

- Optional package/plugin adapters for Codex, Claude, GitHub Copilot, and OpenCode.
- Team-oriented review workflows for shared vault changes.
- Deterministic writeback scenarios that measure duplicate prevention, note updates, and token cost over multi-agent vault activity.

## Later

- Optional embedding backend behind a strict integration boundary.
- UI or TUI for browsing and curating notes.
- Importers from Obsidian-style vaults and existing Markdown knowledge bases.

## Non-goals

- Replacing Markdown as the source of truth.
- Requiring cloud services for local search.
- Making embeddings mandatory for the core workflow.
- Storing credentials, private keys, tokens, or secrets.
