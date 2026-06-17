# Cairn Design

## Status

Accepted for product design.

## Date

2026-06-17

## Context

Cairn started as `okf-vault`, a local-first knowledge vault for a small
engineering team. The product direction is now broader: an agent-ready second
brain for individuals and teams across engineering, support, product, personal
knowledge, and other domains.

The core problem is not storage. Markdown files already store knowledge well.
The problem is operational discipline:

- agents and people must search before solving;
- search must return small snippets before full documents;
- useful knowledge must be captured after solving;
- duplicate notes must be avoided;
- the vault must work with many agent tools, not one vendor;
- everything must remain useful as plain files.

Open Knowledge Format (OKF) is a good structural baseline, but it does not solve
retrieval quality, duplicate prevention, or agent workflow by itself. Cairn uses
OKF-compatible Markdown as the file contract and adds the workflow around it.

## Decision

Build Cairn as a zero-dependency Python CLI over a Markdown vault.

The MVP architecture has five layers:

1. **Vault files**: Markdown concepts, `SCHEMA.md`, templates, `index.md`,
   `log.md`, and generated agent guides.
2. **Config and index**: `.cairn/config.json` and `.cairn/index.db`. Both are
   rebuildable or generated state; Markdown remains authoritative.
3. **Core CLI**: `cairn init`, `search`, `show`, `add`, `update`, `capture`,
   `index`, `validate`, `doctor`, `guide refresh`, and `profile`.
4. **Profiles**: `personal`, `engineering`, `support`, `product`, and `custom`.
   Profiles generate defaults but do not lock the vault to a domain.
5. **Agent adapters**: generated `AGENTS.md` first, tool-specific files later.
   Plugins, slash commands, MCP, and UI are future adapters that call the same
   core.

The public positioning is:

> Cairn is an agent-ready second brain for people and teams.

The core technical principle is:

> Search snippets first, open only selected documents, and update existing
> knowledge before creating new files.

## Architecture

```text
cairn core
├── vault files
│   ├── Markdown concepts
│   ├── SCHEMA.md
│   ├── AGENTS.md
│   ├── index.md / log.md
│   └── _templates/
├── local state
│   ├── .cairn/config.json
│   └── .cairn/index.db
├── CLI commands
│   ├── init/search/show
│   ├── add/update/capture
│   ├── index/validate/doctor
│   └── guide/profile/sync
└── future adapters
    ├── Claude Code
    ├── Codex
    ├── OpenCode
    ├── GitHub Copilot
    └── MCP/plugins/slash commands
```

### Files

Markdown files are the source of truth. A concept file has YAML frontmatter and
a Markdown body. Required fields are `type`, `title`, `description`, `tags`,
and `timestamp`. Cairn adds optional retrieval fields: `aliases`, `systems`, and
`signals`.

### Search

SQLite FTS5 is the primary index. The query result returns metadata and
snippets, not full bodies. Agents call `cairn show` only after choosing which
documents are worth opening.

### Profiles

Profiles are generated defaults:

- `personal`: notes, learning, references, personal workflows.
- `engineering`: bugs, runbooks, incidents, decisions, libraries.
- `support`: triage, common issues, escalation, FAQs.
- `product`: decisions, requirements, stakeholders, discovery, metrics.
- `custom`: minimal starting point.

The core does not hardcode domain folders or types. It reads the active schema.

### Agent Guides

`AGENTS.md` is the canonical guide. `CLAUDE.md`, `CODEX.md`, and future
tool-specific files are generated adapters. They must not contain separate
business logic; they only teach agents how to use the CLI and vault rules.

## Data Flow

### Retrieval

1. User asks a question or reports a problem.
2. Agent runs `cairn search "<query>" --json`.
3. Agent reads snippets and paths.
4. Agent opens at most top relevant documents with `cairn show`.
5. Agent answers using selected knowledge and current context.

### Capture

1. User/agent finishes solving or documenting something.
2. Agent offers to remember it.
3. Cairn searches for related docs.
4. If a same/similar doc exists, agent updates it with `cairn update`.
5. Otherwise Cairn creates a new concept with `cairn add`.
6. Cairn updates `timestamp`, SQLite index, `index.md`, and `log.md`.

### Maintenance

1. `cairn validate` checks schema and OKF subset.
2. `cairn doctor` reports health issues.
3. `cairn guide refresh` regenerates agent guidance from current schema.

## Alternatives Considered

### Engineering-Only Tool

Rejected as the product default. It is easier to explain to developers, but it
would exclude support, product, personal notes, and general team knowledge.
Engineering remains a built-in profile.

### Obsidian-First Vault

Rejected as the foundation. Obsidian compatibility is useful, but Cairn should
not depend on Obsidian conventions or plugins. Standard Markdown and OKF links
come first. Wikilinks can be generated later as optional ergonomics.

### MCP-First Memory Server

Rejected for the MVP. MCP is useful later, but a CLI/file core is simpler,
auditable, works in restricted environments, and supports tools without plugin
systems.

### Vector Search / RAG First

Rejected for the MVP. Full-text search plus structured metadata should be
measured before adding embeddings, model dependencies, or local LLM complexity.
Semantic search becomes justified only if retrieval evals show textual search
cannot meet the target.

### Google OKF Reference Implementation

Rejected as a dependency. The OKF format is useful, but the reference tooling is
BigQuery/Gemini/ADK-oriented and not aligned with Cairn's zero-dependency
local-first core.

## Error Handling

- Commands must fail with actionable messages and non-zero exit codes.
- `init` must be idempotent and avoid overwriting user files.
- `add` must refuse likely duplicates unless `--force-new` is explicit.
- `search` must degrade gracefully if FTS5 is unavailable.
- `validate` must distinguish errors from warnings.
- `guide refresh` must preserve knowledge docs and only update generated guide
  files.
- Secret scan findings should identify file and reason without printing secret
  values.

## Testing Strategy

### Unit Tests

- frontmatter parser;
- schema parser;
- timestamp validation;
- link extraction;
- secret scanner;
- slug/path generation;
- duplicate candidate scoring.

### Integration Tests

- `init` creates a valid vault for each profile;
- `index --rebuild` reconstructs search from Markdown;
- `search` returns the expected document in top 3;
- `add` creates a concept and updates index/log;
- `update` modifies timestamp and index;
- `validate --strict` passes sample vaults.

### Retrieval Evals

Create a small fixture set with representative questions/errors per profile.
Each eval maps a query to expected concept paths. The target is that the correct
document appears in top 3 for the majority of realistic queries before any
semantic search is considered.

## Open Source Readiness

The public repository should make the value obvious without requiring a working
plugin:

- README with positioning and OKF references;
- sample vaults for multiple profiles;
- command examples for humans and agents;
- clear local-first/security stance;
- test suite and retrieval eval fixtures;
- architecture/design docs in `docs/`.

## Consequences

- The CLI is the stable API. Adapters can change without breaking vaults.
- Profiles make the product broad without adding product-specific core logic.
- OKF compatibility gives structure without vendor dependency.
- Retrieval quality must be measured, not assumed.
- Future plugins and slash commands stay small because the core owns behavior.
