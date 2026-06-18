# Changelog

All notable Cairn changes are tracked here.

## Unreleased

### Added

- `cairn add` and `cairn capture` can read note bodies from `--body-file` or `--body-stdin`.
- `cairn update` can append from `--append-file` or `--append-stdin`.
- `cairn retrieve --ranker auto` tries BM25 first and falls back to RRF only when no context is returned.
- `cairn similar` results include `kind` labels: `duplicate_candidate` or `related`.

### Changed

- Multi-section note bodies that already start with a Markdown heading are preserved without adding a duplicate `# Context` heading.
- `cairn update` accepts absolute document paths inside the vault, reports the normalized vault-relative path, and refreshes the note timestamp only when new text is appended.
- Internal research, plans, and reports are excluded from the public documentation tree.

## 0.1.0 - 2026-06-17

Initial public release.

### Added

- Vault initialization profiles for personal, engineering, product, support, and custom use.
- Markdown/frontmatter validation.
- Common secret detection during validation without echoing detected values.
- Incremental SQLite FTS search index.
- Metadata filters for type, tag, and system.
- Budgeted retrieval for low-context agent workflows.
- Retrieval redaction for common secret-like values.
- Passage-based retrieval for section-level context packets.
- Experimental RRF ranker for noisy or lexically varied document and passage queries.
- Partial document reads by line range, section, and snippet.
- Similar-note checks before creating duplicates.
- Lightweight fingerprint fallback for near-duplicate checks with extra terms.
- Note creation and idempotent append updates.
- Agent guide generation for Codex, Claude, OpenCode, and generic agents.
- Vault stats, doctor, export, and import commands.
- Export blocking when common secret-like values are detected.
- CI, contribution guide, roadmap, and example vault.
- Categorized deterministic search benchmark with golden ranking checks and token metrics.
- Expanded onboarding documentation and example walkthroughs.
