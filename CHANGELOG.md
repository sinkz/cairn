# Changelog

All notable Cairn changes are tracked here.

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
