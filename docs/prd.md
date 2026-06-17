# PRD - Cairn

> **Agent-ready second brain for people and teams.**
> Local-first Markdown/OKF knowledge vault operated by humans and AI agents.

---

## 0. How To Use This Document

This PRD is the product specification for Cairn. It replaces the earlier
`okf-vault` framing with a broader product: a local-first second brain that can
serve individuals, engineering teams, support teams, product teams, and any AI
agent capable of reading files and running a CLI.

Read sections 1-5 for product context. Use sections 6-14 as the implementation
contract. If anything is ambiguous, prefer the simplest local implementation
that keeps files as the source of truth.

**Non-negotiable principles:**

1. **Local-first.** The core product must not require network access at runtime.
2. **Tool-agnostic.** Cairn must work with Codex, Claude Code, OpenCode,
   GitHub Copilot, and simple harnesses that only read files/run shell commands.
3. **Domain-agnostic.** Engineering is a first use case, not the product
   boundary. Support, product, operations, study, and personal notes must fit.
4. **Files are the source of truth.** Markdown documents own the knowledge.
   SQLite is only a rebuildable search index.
5. **OKF-compatible by construction.** Cairn documents follow the useful subset
   of Open Knowledge Format: one concept per Markdown file, YAML frontmatter,
   standard Markdown links, `index.md`, and `log.md`.
6. **Token efficiency.** Agents search snippets first, then open at most the
   top relevant documents. They never read the whole vault.
7. **Stdlib core.** The core CLI should run on Python 3.11+ using the standard
   library only. Third-party dependencies, plugins, MCP, or UI belong outside
   the core.

---

## 1. Problem

People and teams repeatedly solve the same problems and lose the solution.
Useful knowledge stays in chat threads, tickets, meeting notes, agent sessions,
temporary docs, or someone's memory. Months later, the same bug, process,
decision, customer issue, product question, or operational task appears again
and the discovery work starts from zero.

Existing tools do not close the loop:

- **Traditional wikis** have high capture friction and often lack consistent
  structure, tags, error text, examples, or update discipline.
- **Obsidian-style second brains** are powerful for humans, but not always
  optimized for agents that must retrieve context under a token budget.
- **Agent conversations** are useful in the moment, but are usually ephemeral,
  not shared, not versioned, and not searchable from another tool.
- **Ad-hoc Markdown folders** are readable, but without conventions and
  validation they drift into duplicates and inconsistent naming.

The key insight: AI agents are good at the parts humans skip. They can search
before solving, offer to capture after solving, update indexes, preserve links,
and keep the vault tidy if the rules are explicit and enforceable.

---

## 2. Solution In One Sentence

Cairn is a local CLI that operates an OKF-compatible Markdown vault with
structured profiles, SQLite full-text search, validation, dedupe checks, and
agent guides so humans and AI agents can capture, search, and reuse knowledge
without wasting context.

---

## 3. Product Positioning

Cairn is not "a wiki app" and not "a RAG platform." It is a portable knowledge
workflow for agentic work.

**Tagline:**

> Cairn is an agent-ready second brain for people and teams.

**Short description:**

> Local-first Markdown knowledge vault that helps humans and AI agents capture,
> search, and reuse knowledge without wasting context.

**Differentiators:**

- Works with plain files and Git.
- Uses OKF as a lightweight interoperability baseline.
- Optimizes retrieval for agents by returning snippets and paths first.
- Includes anti-duplication rules and profile-specific templates.
- Generates agent guides instead of depending on a single agent product.
- Can start personal and grow into a team vault.

---

## 4. Why OKF

Open Knowledge Format (OKF), published by Google Cloud in June 2026, formalizes
the "LLM wiki" shape: a directory of Markdown files where each file is one
concept, YAML frontmatter carries structured metadata, and the path acts as the
concept identity.

Cairn adopts OKF as a **file-format convention**, not as a dependency:

- Low adoption cost: Markdown + frontmatter was already the right base.
- Future interoperability: OKF-aware tools can read Cairn vaults.
- No vendor lock-in: Cairn does not depend on Google Cloud, BigQuery, Gemini,
  the enrichment agent, or the reference visualizer.
- Safe fallback: if OKF stalls, Cairn still owns useful Markdown files.

Cairn intentionally uses a stricter subset than OKF requires. OKF only requires
`type`; Cairn also requires `title`, `description`, `tags`, and `timestamp` for
better search, previews, validation, and agent behavior.

---

## 5. Non-Goals

- No required cloud service.
- No runtime network calls in the core CLI.
- No GCP, BigQuery, Gemini, or Knowledge Catalog integration in the MVP.
- No vector search, embeddings, local LLM, or RAG in the MVP.
- No long-running server, web API, daemon, or hosted sync in the MVP.
- No visual editor or GUI in the MVP.
- No MCP server in the MVP.
- No secrets manager. Cairn documents processes and knowledge, not credentials.
- No product-specific lock-in. Plugins and slash commands are adapters, not the
  foundation.

---

## 6. Personas And Core Use Cases

### Individual Knowledge Worker

Uses Cairn as a personal second brain for notes, workflows, learning, recurring
tasks, and decisions. They may use it with any AI agent or directly from a CLI.

### Engineer

Captures bugs, incident fixes, library gotchas, architecture decisions, setup
steps, runbooks, and debugging paths. Before solving, the agent searches the
vault for similar errors and opens only relevant docs.

### Support Analyst

Captures recurring customer issues, triage procedures, escalation paths, system
behaviors, ticket patterns, and resolution templates.

### Product Owner / Product Manager

Captures product decisions, requirements, stakeholder notes, discovery insights,
rituals, metrics definitions, and release/process knowledge.

### Team Owner

Maintains the profile, schema, tags, templates, and health of a shared team
vault. Runs validation and dedupe checks in CI or pre-commit.

### AI Agent

Reads `AGENTS.md` or a tool-specific guide, searches before answering, opens at
most top results, updates existing documents before creating duplicates, and
offers to capture new reusable knowledge after solving a problem.

---

## 7. Primary Loops

### 7.1 Retrieval Loop

```
[1] ASK      -> user asks a question or reports a problem
[2] SEARCH   -> agent runs `cairn search "<query>" --json`
[3] TRIAGE   -> agent reads snippets and paths only
[4] OPEN     -> agent opens at most the top relevant documents
[5] ANSWER   -> agent uses retrieved knowledge plus current context
```

### 7.2 Capture Loop

```
[1] SOLVE    -> user and/or agent solve a problem or document a process
[2] PROPOSE  -> agent asks whether to save reusable knowledge
[3] DEDUPE   -> Cairn searches for existing related documents
[4] UPDATE   -> if same topic exists, update it
[5] CREATE   -> otherwise create a new concept from the right template
[6] INDEX    -> update SQLite index, index.md, and log.md
```

### 7.3 Maintenance Loop

```
[1] CHECK    -> `cairn validate` verifies schema and OKF subset
[2] DOCTOR   -> `cairn doctor` reports vault health issues
[3] REFRESH  -> `cairn guide refresh` regenerates agent guides
[4] TUNE     -> humans adjust SCHEMA.md, templates, and profiles
```

---

## 8. Vault Format

### 8.1 Default Structure

```text
cairn-vault/
├── AGENTS.md                  # canonical, tool-agnostic agent guide
├── CLAUDE.md                  # optional generated adapter
├── CODEX.md                   # optional generated adapter
├── SCHEMA.md                  # human-owned profile schema: types, tags, rules
├── index.md                   # root progressive-disclosure index
├── log.md                     # chronological update log, newest first
├── .gitignore
├── .cairn/
│   ├── config.json            # local config, profile, excluded paths
│   └── index.db               # disposable SQLite FTS index
├── _templates/
│   ├── concept.md
│   ├── runbook.md
│   ├── decision.md
│   ├── process.md
│   └── note.md
├── knowledge/
├── processes/
├── decisions/
├── references/
├── notes/
└── inbox/                     # ephemeral, excluded from default retrieval
```

Profiles may create different top-level folders. The core must not assume a
fixed domain taxonomy beyond reserved files and configured exclusions.

### 8.2 Reserved Files

Reserved OKF/Cairn files must not be treated as concepts:

- `index.md`
- `log.md`
- `AGENTS.md`
- `CLAUDE.md`
- `CODEX.md`
- `SCHEMA.md`

### 8.3 Frontmatter Schema

Every concept is a Markdown file with a YAML frontmatter block followed by a
Markdown body.

| Field | Required | Type | Rule |
| --- | --- | --- | --- |
| `type` | yes | string | Must belong to the active profile's type set. |
| `title` | yes | string | Human-readable display name. |
| `description` | yes | string | One-sentence summary used for search previews. |
| `tags` | yes | list[string] | Tags should belong to the active profile vocabulary. |
| `timestamp` | yes | ISO 8601 | Last meaningful update time. |
| `resource` | no | URI/string | Canonical resource or external/internal link. |
| `aliases` | no | list[string] | Alternate names and terms users may search for. |
| `systems` | no | list[string] | Systems, products, apps, areas, or teams involved. |
| `signals` | no | list[string] | Error strings, codes, symptoms, or searchable phrases. |
| extensions | no | any | Unknown keys are preserved and not rejected. |

`aliases`, `systems`, and `signals` are Cairn extensions. They are optional but
important for search quality, especially when users remember different words
months later.

### 8.4 Links

Use standard Markdown links. Prefer bundle-root absolute paths:

```markdown
See [Access request process](/processes/access-request.md).
```

Wikilinks may be generated later for Obsidian ergonomics, but standard Markdown
links are canonical for OKF compatibility and validation.

---

## 9. Profiles

Profiles initialize folder structure, type vocabulary, tag vocabulary,
templates, and agent-guide text. They are defaults, not hardcoded behavior.

### 9.1 Built-In Profiles

- `personal`: notes, learning, habits, references, personal processes.
- `engineering`: bugs, runbooks, decisions, libraries, architecture, incidents.
- `support`: customer issues, triage, procedures, escalation, FAQs.
- `product`: decisions, requirements, discovery, stakeholders, metrics.
- `custom`: minimal schema for users who want to define everything.

### 9.2 Profile Files

Profiles are represented by generated Markdown/config files inside the vault:

- `SCHEMA.md`: human-readable source of truth for types and tags.
- `_templates/*.md`: body templates for concepts.
- `.cairn/config.json`: machine-readable settings.
- `AGENTS.md`: guide for agents.

Changing the profile after initialization must not delete existing knowledge.
The `profile apply` command may add missing templates/tags but must avoid
destructive edits.

---

## 10. Agent Guides

Cairn's core integration surface is generated guidance, not a product-specific
plugin.

### 10.1 Canonical Guide

`AGENTS.md` is the canonical tool-agnostic guide. It must include:

- What the vault is.
- The active profile and where to find `SCHEMA.md`.
- The retrieval loop.
- The capture loop.
- The top-3 rule.
- Anti-duplication rules.
- Security rules: never write secrets.
- CLI examples.

### 10.2 Tool-Specific Adapters

`cairn guide refresh` may generate tool-specific files:

- `CLAUDE.md` for Claude Code.
- `CODEX.md` or equivalent guidance for Codex.
- OpenCode/GitHub Copilot adapter files when conventions are stable.
- Future slash-command/plugin manifests.

Adapters must remain thin. They translate agent UX into Cairn CLI commands and
must not implement independent business logic.

---

## 11. CLI Specification

Command root: `cairn`.

The core is implemented in Python 3.11+ using `argparse`, `pathlib`, `sqlite3`,
`json`, `datetime`, `re`, and other standard-library modules only.

### 11.1 `cairn init [--path .] [--profile personal|engineering|support|product|custom]`

Initializes a vault. Creates `.cairn/config.json`, `.cairn/index.db`,
`AGENTS.md`, `SCHEMA.md`, templates, `index.md`, `log.md`, `.gitignore`, and
profile folders. Idempotent: never overwrites existing user files without an
explicit force flag.

### 11.2 `cairn search "<query>" [--type T] [--tag X] [--limit 3] [--json]`

Searches the local SQLite FTS index using BM25 ranking. Default limit is 3.
Returns path, type, title, tags, score, and snippets. It never returns full
document bodies unless explicitly asked through a separate command.

Aliases:

- `cairn recall`

### 11.3 `cairn show <path> [--json]`

Prints a concept after the user or agent has selected it from search results.
Agents should call this for at most the top relevant documents.

### 11.4 `cairn add`

Creates a new concept. Supports interactive mode and non-interactive agent mode:

```bash
cairn add \
  --type Runbook \
  --title "Fix deploy 403" \
  --description "How to fix deploy 403 caused by missing permission." \
  --tags deploy,permission \
  --folder processes/deploy \
  --body-file /tmp/body.md
```

Before writing, `add` must run duplicate detection. If related docs exist, it
prints candidates and refuses to create unless `--force-new` is passed.

Alias:

- `cairn remember`

### 11.5 `cairn update <path>`

Updates an existing concept. The first MVP form may append a section or replace
the file from `--body-file`. It must update `timestamp`, reindex, and prepend
`log.md`.

### 11.6 `cairn capture`

Guided capture command for humans and agents. It asks what was learned,
searches for existing docs, chooses update vs create, then writes through
`add`/`update`. This is the most ergonomic user-facing capture flow.

### 11.7 `cairn index [--rebuild]`

Builds or rebuilds `.cairn/index.db` from Markdown files. The database is
discardable; deleting it must never lose knowledge.

### 11.8 `cairn validate [--strict]`

Validates the vault. Exit code `0` if valid, `1` if invalid. `--strict` turns
warnings into failures.

Alias:

- `cairn check`

### 11.9 `cairn doctor`

Reports vault health:

- duplicate candidates;
- broken internal links;
- missing tags;
- unused tags;
- very long documents;
- documents not matching templates;
- stale agent guides;
- search index drift;
- possible secrets.

### 11.10 `cairn guide refresh [--target agents,claude,codex,opencode]`

Regenerates agent guides from `SCHEMA.md`, `.cairn/config.json`, and built-in
guide templates. Must preserve hand-written knowledge docs.

### 11.11 `cairn profile list|show|apply`

Lists profiles, previews a profile, or applies profile defaults to an existing
vault. Applying a profile is additive and non-destructive by default.

### 11.12 `cairn sync`

Optional Git wrapper for team vaults:

```bash
git pull --rebase && git push
```

This belongs after the core loop is stable.

---

## 12. Search And Token Economy

Token cost comes from document content entering the agent context, not from the
local search command. Therefore:

1. The agent runs `cairn search --json`.
2. The agent reads snippets and paths.
3. The agent opens at most the top relevant documents with `cairn show`.
4. The agent never reads the full vault.

SQLite FTS5 is the preferred search engine. The implementation should confirm
that the local Python `sqlite3` build supports FTS5. If FTS5 is unavailable,
fallback order is:

1. `ripgrep` if available;
2. SQLite `LIKE`;
3. simple stdlib file scan.

The index should include frontmatter fields and body text, with extra weight for
`title`, `description`, `aliases`, `systems`, `signals`, and `tags`.

---

## 13. Validation And Security

### 13.1 Validation Errors

Validation fails when:

1. A concept file lacks parseable frontmatter.
2. Required fields are missing or empty.
3. `type` is not present in `SCHEMA.md`.
4. Tags violate the active profile vocabulary, unless the profile allows free
   tags.
5. `timestamp` is not valid ISO 8601.
6. Reserved files are malformed.

### 13.2 Strict Warnings

Warnings become failures with `--strict`:

1. Broken internal links.
2. Concepts without tags.
3. Concepts without expected body sections for their type.
4. Documents that are likely duplicates.
5. Agent guides that are stale relative to `SCHEMA.md`.

### 13.3 Secret Scanning

Cairn must never encourage storing credentials. The scanner should flag high-risk
patterns such as:

- private key blocks;
- AWS-style keys;
- long high-entropy hex/base64 tokens;
- `password=`, `senha=`, `secret=`, `token=`;
- obvious credential headings in access/process docs.

The scanner is intentionally conservative. Users can document how to get access,
but not the credential itself.

---

## 14. Open Source Packaging

Cairn should be viable as a public portfolio-grade project.

Minimum public surface:

- clear README;
- documented philosophy and OKF reference;
- zero-dependency core;
- tests for parser, validator, index, search, and init;
- sample vaults for `personal`, `engineering`, `support`, and `product`;
- benchmark/eval dataset for retrieval quality;
- agent-guide examples for multiple tools.

The package name and binary should be `cairn` if available. If package registry
collision occurs, keep the product name Cairn and use a scoped/disambiguated
package name.

---

## 15. Future Adapters

Plugins, extensions, slash commands, MCP, and viewers are future adapters. They
must call the same core CLI and file model.

Possible slash commands:

```text
/cairn-search
/cairn-recall
/cairn-remember
/cairn-update
/cairn-doctor
/cairn-refresh
```

Possible adapters:

- Claude Code command pack.
- Codex guide/command pack.
- OpenCode integration.
- GitHub Copilot instructions.
- MCP server exposing search/show/add/update.
- Offline HTML graph viewer with no CDN.

Adapters are valuable for UX, but the MVP must work without them.

---

## 16. Implementation Roadmap

### Phase 0 - CLI Skeleton And Init

- Python package skeleton.
- `cairn` entrypoint.
- `argparse` command tree.
- `cairn init` with profiles, `AGENTS.md`, `SCHEMA.md`, templates, `.gitignore`,
  `.cairn/config.json`, and empty index.
- Acceptance: initialized vault validates.

### Phase 1 - Validation And Indexing

- Minimal frontmatter parser using stdlib.
- Schema parser for `SCHEMA.md`.
- `cairn validate`.
- SQLite FTS5 index builder.
- `cairn search --json`.
- `cairn show`.
- Acceptance: saved fixture docs are searchable and validate.

### Phase 2 - Capture Loop

- `cairn add` non-interactive mode.
- duplicate detection before create;
- `cairn update`;
- `index.md` and `log.md` maintenance;
- `cairn capture` guided flow.
- Acceptance: update-vs-create flow prevents obvious duplicate docs.

### Phase 3 - Agent Guides And Profiles

- `cairn guide refresh`.
- profile list/show/apply.
- generated `AGENTS.md`, `CLAUDE.md`, and `CODEX.md` examples.
- sample vaults for personal, engineering, support, product.
- Acceptance: an agent reading only generated guidance can search, show, add,
  update, and avoid duplicates in a clean session.

### Phase 4 - Health And Team Readiness

- `cairn doctor`;
- secret scanner;
- pre-commit helper;
- optional `cairn sync`;
- retrieval benchmark/eval suite.
- Acceptance: CI can validate a sample vault and run retrieval evals.

### Future

- MCP server.
- tool plugins/extensions;
- slash commands;
- offline HTML viewer;
- local semantic search only if textual search fails measured evals.

---

## 17. Success Criteria

- **Capture without friction:** reusable knowledge can be saved in under 30
  seconds of human effort.
- **Recovery quality:** documented knowledge appears in top 3 search results for
  representative queries.
- **Token efficiency:** search returns snippets first; agents open only selected
  docs.
- **Low lock-in:** vault remains useful as Markdown without Cairn installed.
- **Multi-domain fit:** personal, engineering, support, and product sample vaults
  all work without changing core code.
- **Agent portability:** generated guides work across at least two agent tools.
- **Validation:** sample vaults pass `cairn validate --strict`.
- **Safety:** secret scan catches common credential leaks.

---

## 18. References

- Google Cloud announcement: <https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing>
- Google reference repository: <https://github.com/GoogleCloudPlatform/knowledge-catalog>
- OKF directory: <https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf>
- OKF v0.1 spec: <https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md>

---

_End of PRD. Implementation should preserve the local-first, tool-agnostic,
domain-agnostic core._
