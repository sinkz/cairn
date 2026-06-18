# Changelog

All notable ApolloKairn changes are tracked here.

## Unreleased

### Added

- Added `apollokairn vault` for local multi-vault registration, active-vault
  switching, JSON-friendly discovery, and `--vault` resolution from any
  working directory.

## 0.1.4 - 2026-06-18

### Added

- Added opt-in local usage metrics through `apollokairn usage`, with redacted
  JSONL events and static HTML/JSON vault reports under `.cairn/`.

## 0.1.3 - 2026-06-18

### Changed

- Glossary aliases are now eligible during the first retrieval pass instead of
  only as an empty-result fallback.
- Search, passage retrieval, and RRF ranking now use precision-preserving
  grouped glossary expansion, so approved aliases such as `k8s` can match
  `kubernetes` without turning the whole query into a broad OR search.

## 0.1.2 - 2026-06-18

### Changed

- Renamed the public project to ApolloKairn.
- Added `apollokairn` as the primary CLI command and `ak` as a short alias.
- Kept `cairn` as a compatibility alias for the rename window.
- Renamed public release assets, install docs, and GitHub Pages links to the
  ApolloKairn namespace.

## 0.1.1 - 2026-06-18

### Added

- `apollokairn add` and `apollokairn capture` can read note bodies from `--body-file` or `--body-stdin`.
- `apollokairn update` can append from `--append-file` or `--append-stdin`.
- `apollokairn retrieve --ranker auto` tries BM25 first and falls back to RRF only when no context is returned.
- `apollokairn similar` results include `kind` labels: `duplicate_candidate` or `related`.
- `apollokairn vocab` manages a deterministic top-level `glossary.md` for approved aliases such as `k8s` and `kubernetes`.
- `apollokairn search --explain` and `apollokairn retrieve --explain` expose deterministic ranking diagnostics without treating scores as confidence.
- `apollokairn setup-agent` supports Hermes and GitHub Copilot generated instruction files.
- Machine-readable `--json` output is available across operational commands.
- Pre-write policy validation blocks invalid schema values and common secret-like values before new content is written.
- Deterministic writeback benchmark covers create, update, no-op, conflict, and duplicate-avoidance decisions.
- Standalone release binaries and quick install scripts are available for Linux, macOS, and Windows.
- GitHub Pages overview with EN/PT-BR copy and benchmark data loaded from JSON.

### Changed

- Multi-section note bodies that already start with a Markdown heading are preserved without adding a duplicate `# Context` heading.
- `apollokairn update` accepts absolute document paths inside the vault, reports the normalized vault-relative path, and refreshes the note timestamp only when new text is appended.
- Internal research, plans, and reports are excluded from the public documentation tree.
- Public docs now position ApolloKairn as agent-optimized and agent-agnostic, with Markdown and SQLite as the product-independent core.
- Roadmap now separates shipped capabilities from active priorities, next work, and later bets.

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
