# ApolloKairn Usage Guide

This guide explains what ApolloKairn is for, how to configure a vault, and when to use
each command.

## What ApolloKairn Is For

ApolloKairn is a local Markdown knowledge vault optimized for AI-agent workflows. It
helps agents save reusable knowledge after solving problems, making decisions,
documenting processes, or learning recurring patterns.

ApolloKairn does not depend on a specific agent product. Any harness that can run CLI
commands can use the same vault and the same Markdown files. It is most useful
when an agent searches first, retrieves only the necessary context, solves the
task, and writes back reusable knowledge.

Typical use cases:

- debugging notes and recurring bug fixes;
- operational runbooks;
- support escalation procedures;
- product or architecture decisions;
- library references and access/process notes;
- personal notes that should be searchable by an agent later.

The core idea is simple: agents should search first, open only the most relevant
documents, and write back reusable knowledge after the work is solved.

## Installation And First Run

Install from the repository root:

```bash
python -m pip install -e .
apollokairn --help
```

Or run without installing:

```bash
export PYTHONPATH="$PWD/src"
python -m cairn --help
```

PowerShell:

```powershell
$env:PYTHONPATH = Join-Path (Resolve-Path .).Path "src"
python -m cairn --help
```

After creating or editing notes, run `apollokairn index`. Search and retrieve use the
local index; if it is missing or stale, `apollokairn doctor` will tell you.

## Creating a Vault

```bash
apollokairn init --path ~/brain --profile engineering
apollokairn validate --path ~/brain
apollokairn index --path ~/brain --rebuild
apollokairn doctor --path ~/brain
```

Profiles define default folders, types, and tags.

| Profile | Use case |
| --- | --- |
| `personal` | Personal notes, learning, workflows, references |
| `engineering` | Bugs, runbooks, incidents, libraries, decisions |
| `product` | Requirements, discovery, metrics, release decisions |
| `support` | Support triage, procedures, FAQs, escalations |
| `custom` | Minimal starting point for your own schema |

The command creates:

| Path | Purpose |
| --- | --- |
| `AGENTS.md` | Instructions for agents using the vault |
| `SCHEMA.md` | Allowed document types and tags |
| `index.md` | Human entry point for the vault |
| `log.md` | Chronological update log |
| `.cairn/config.json` | ApolloKairn settings |
| `_templates/concept.md` | Starting template for new notes |
| domain folders | `knowledge`, `processes`, `decisions`, `references`, `notes`, `inbox` |

The vault may also contain a top-level `glossary.md`. ApolloKairn treats it as a
reserved control file, not as a regular note.

## Configuration

ApolloKairn stores local settings in `.cairn/config.json`.

Example:

```json
{
  "exclude": ["inbox"],
  "generated_guides": ["AGENTS.md"],
  "profile": "engineering",
  "search_limit": 3
}
```

Important fields:

| Field | Purpose |
| --- | --- |
| `profile` | The profile used when the vault was initialized |
| `search_limit` | Suggested default result limit for agents |
| `exclude` | Folders or patterns ignored by validation and indexing |
| `generated_guides` | Agent guide files managed by ApolloKairn |

Use `exclude` for scratch areas, private inboxes, generated files, and anything
that should not be indexed.

## Document Format

Each reusable concept should be one Markdown file with frontmatter:

```markdown
---
type: Runbook
title: Deploy 403 after token rotation
description: Fixes deploy failures caused by stale workspace access tokens.
tags: [bug, deploy]
timestamp: 2026-06-17T12:00:00-03:00
aliases: [deploy forbidden, token 403]
systems: [ci, deployment]
signals: [http 403, forbidden, workspace access]
---

# Context

What happened and when this applies.

# Diagnosis

How to recognize the problem.

# Resolution

How to solve it.
```

Required fields:

- `type`
- `title`
- `description`
- `tags`
- `timestamp`

Useful optional fields:

- `aliases`: alternate names people or agents might search for;
- `systems`: affected systems, products, repositories, services, or domains;
- `signals`: symptoms, errors, logs, status codes, or trigger phrases.

Never store secrets, tokens, passwords, private keys, or credentials.

## Glossary And Deterministic Aliases

Use `glossary.md` for stable vocabulary differences that strict lexical search
cannot infer, such as `k8s` and `kubernetes`. The glossary is explicit data in
the vault, so it can be reviewed and versioned like any other important file.

```markdown
# Glossary

## Kubernetes

aliases: k8s, kube
status: approved
scope: engineering
```

ApolloKairn keeps the default search conservative. `search` and `retrieve` first run
the exact BM25 query. Only when that returns no rows, ApolloKairn expands approved
glossary terms and aliases and retries with a cheap OR query. This keeps common
queries stable while still covering curated synonym gaps.

Manage the glossary with:

```bash
apollokairn vocab add-term Kubernetes --alias k8s --alias kube --path ~/brain
apollokairn vocab add-alias Kubernetes k8s-prod --path ~/brain
apollokairn vocab add-term Kubernetes --alias k8s --path ~/brain --json
apollokairn vocab suggest "kubernetes rollback" --path ~/brain --json
apollokairn vocab validate --path ~/brain --json
```

`vocab suggest` never writes to the vault. It reports deterministic candidates
from local notes so a human or agent can decide whether an alias should become
approved vocabulary.

## Command Reference

### `apollokairn init`

Creates a new vault.

```bash
apollokairn init --path ~/brain --profile engineering
apollokairn init --path ~/brain --profile engineering --json
```

Use this once per vault. Running it again is safe; existing files are skipped.
With `--json`, the result includes `root`, `created`, and `skipped`.

### `apollokairn validate`

Checks whether Markdown notes follow `SCHEMA.md` and required frontmatter rules.
It also blocks common secret-like values such as access keys, provider tokens,
and private key blocks without printing the detected value.

```bash
apollokairn validate --path ~/brain
apollokairn validate --path ~/brain --json
```

Use it before indexing, before committing a vault, or when an agent created or
edited notes.

### `apollokairn add` and `apollokairn capture`

Creates a reusable note with valid ApolloKairn frontmatter.

```bash
apollokairn add --path ~/brain \
  --title "Deploy 403 after token rotation" \
  --description "Fixes stale CI authorization after token rotation." \
  --type Runbook \
  --tag bug \
  --tag deploy \
  --system ci \
  --signal "HTTP 403" \
  --body "Deploy failed after token rotation. Update the CI secret and rerun the failed job."
```

`capture` is an alias with the same behavior. Use these after a task is solved
and the knowledge is likely to be useful again.

Before writing, ApolloKairn validates the rendered note against `SCHEMA.md` and scans
the new content for common secret-like values. Invalid type/tag combinations or
detected secrets fail before a Markdown file is created. With `--json`, policy
failures return `ok`, `path`, `error_count`, and `errors`.

The CLI body argument is best for short text. For multi-section notes, create
the body in a Markdown file and pass it with `--body-file`:

```bash
apollokairn capture --path ~/brain \
  --title "Webhook 400 after SDK upgrade" \
  --description "Fixes provider webhook requests rejected after a schema change." \
  --type Runbook \
  --tag bug \
  --system support-api \
  --body-file ./webhook-400-body.md
```

Use `--body-stdin` when another tool or agent generates the body:

```bash
cat ./webhook-400-body.md | apollokairn capture --path ~/brain \
  --title "Webhook 400 after SDK upgrade" \
  --description "Fixes provider webhook requests rejected after a schema change." \
  --type Runbook \
  --tag bug \
  --body-stdin
```

If the body starts with a Markdown heading, ApolloKairn preserves it as-is. If it is
plain text, ApolloKairn wraps it in a `# Context` section.

For agent workflows, use `--json` to receive the write result and `--dry-run`
to preview the target path without creating the file:

```bash
apollokairn capture --path ~/brain --title "Draft note" --description "Preview." --tag workflow --body "..." --dry-run --json
```

### `apollokairn update`

Appends text to an existing note if the same text is not already present.

```bash
apollokairn update knowledge/deploy-403.md --path ~/brain --append "Add the new verification step."
apollokairn update knowledge/deploy-403.md --path ~/brain --append-file ./deploy-403-update.md
cat ./deploy-403-update.md | apollokairn update knowledge/deploy-403.md --path ~/brain --append-stdin
```

Use it when `apollokairn similar` finds an existing note that should be expanded
instead of duplicated. The document argument can be a vault-relative path or an
absolute path inside the vault. Updates are idempotent and refresh the note
timestamp only when new text is actually appended.

Agents can request machine-readable results, preview writes, and guard against
stale files:

```bash
apollokairn update knowledge/deploy-403.md --path ~/brain --append-file ./deploy-403-update.md --dry-run --json
apollokairn update knowledge/deploy-403.md --path ~/brain --append-file ./deploy-403-update.md --expect-sha256 <CURRENT_SHA256> --json
```

The JSON result includes `changed`, `would_change`, `dry_run`, `reason`,
`sha256_before`, and `sha256_after`. When the appended text is already present,
`reason` is `already_present`.
The appended text is scanned for common secret-like values before it is written.
With `--json`, policy failures use the same `ok`, `path`, `error_count`, and
`errors` shape as `capture`.

### `apollokairn index`

Builds or updates the local SQLite FTS index.

```bash
apollokairn index --path ~/brain --rebuild
apollokairn index --path ~/brain
apollokairn index --path ~/brain --json
```

Use `--rebuild` after the first setup or if the index is corrupted. Without
`--rebuild`, indexing is incremental: changed files are updated, removed files
are deleted from the index, and unchanged files are skipped.

### `apollokairn doctor`

Checks vault health and index freshness.

```bash
apollokairn doctor --path ~/brain
apollokairn doctor --path ~/brain --json
```

Use it when search behaves oddly, after manual file edits, or before an agent
session starts. It reports validation errors, missing index, invalid index, or
stale index metadata.

### `apollokairn search`

Searches the vault and returns compact results with snippets.

```bash
apollokairn search "deploy 403 workspace access" --path ~/brain --limit 3
apollokairn search "deploy token rotation kubernetes secret" --path ~/brain --ranker rrf
```

Use search before opening full documents. This is the main token-saving command.
The default `bm25` ranker is strict and stable. Use experimental `--ranker rrf`
when the query may contain extra terms or lexical variants and you want ApolloKairn to
fuse multiple cheap lexical runs.
If a top-level `glossary.md` exists, strict BM25 automatically gets one fallback
attempt with approved aliases only when the exact query returns no rows.

Filters:

```bash
apollokairn search "retry timeout" --path ~/brain --type Decision
apollokairn search "deploy" --path ~/brain --tag deploy
apollokairn search "timeout" --path ~/brain --system checkout
```

JSON output for agents:

```bash
apollokairn search "cache stampede" --path ~/brain --json
apollokairn search "cache stampede" --path ~/brain --json --explain
```

`--explain` wraps results with deterministic ranking diagnostics: score, matched
fields, matched query terms, and an explicit note that scores are not confidence.

### `apollokairn retrieve`

Builds a context packet for an LLM under an approximate token budget.

```bash
apollokairn retrieve "deploy 403" --path ~/brain --limit 3 --budget 800
apollokairn retrieve "deploy 403" --path ~/brain --mode passages --budget 500
apollokairn retrieve "deploy token rotation kubernetes secret" --path ~/brain --ranker rrf --budget 800
apollokairn retrieve "deploy token rotation kubernetes secret" --path ~/brain --ranker auto --budget 800
apollokairn retrieve "reconnecting cache workers" --path ~/brain --mode passages --ranker rrf --budget 500
apollokairn retrieve "reconnecting cache workers" --path ~/brain --mode passages --ranker auto --budget 500
apollokairn retrieve "deploy 403" --path ~/brain --mode passages --budget 500 --json
apollokairn retrieve "deploy 403" --path ~/brain --mode passages --budget 500 --json --explain
```

Use this when an agent needs useful context immediately without manually running
`search` and `show`. The budget uses a simple approximation of 4 characters per
token. Retrieval redacts common secret-like values before printing the context
packet.

Use `--mode passages` when the agent needs the smallest useful sections instead
of full matching documents. Passage output includes the source path, heading,
and line range so the agent can reopen the exact context if needed.

Use `--ranker auto` when you want a safe fallback: ApolloKairn tries strict `bm25`
first and only spends the extra RRF search work when no context is returned.
Use `--ranker rrf` when you explicitly want fused lexical ranking every time.

JSON output returns the same context packet with metadata: query, mode, requested
ranker, ranker actually used, token budget, estimated tokens used, source count,
rendered context, and per-source metadata.
With `--explain`, JSON output is `{ "packet": ..., "explanations": [...] }` and
each explanation includes matched fields/terms plus the score diagnostic note.

Filters work the same way as `search`:

```bash
apollokairn retrieve "retry timeout" --path ~/brain --type Decision --system checkout --budget 600
```

### `apollokairn show`

Opens a document from the vault.

```bash
apollokairn show knowledge/deploy-403.md --path ~/brain
```

Use partial reads to reduce context:

```bash
apollokairn show knowledge/deploy-403.md --path ~/brain --section Diagnosis
apollokairn show knowledge/deploy-403.md --path ~/brain --snippet "workspace access" --context 2
apollokairn show knowledge/deploy-403.md --path ~/brain --lines 20:40
apollokairn show knowledge/deploy-403.md --path ~/brain --section Diagnostico --json
```

Partial reads are useful after `search` identifies the right document but the
agent only needs one section or nearby lines.
Section and snippet selectors are accent-insensitive, so ASCII queries can match
Portuguese headings such as `Solução` or `Diagnóstico`.

### `apollokairn similar`

Finds existing notes before creating a duplicate. It combines indexed lexical
search with a lightweight local fingerprint scan, so it can still catch near
duplicates when the new note contains extra terms.

```bash
apollokairn similar "deploy forbidden token" --path ~/brain --limit 5
```

Use this before adding a new note. If a result is close enough, update the
existing note instead of creating another one.

JSON output is available for agents:

```bash
apollokairn similar "deploy forbidden token" --path ~/brain --json
```

Results include a `kind` field. `duplicate_candidate` means the match is strong
enough to prefer updating the existing note. `related` means the note is useful
context, but the agent should inspect it before deciding whether to update or
create a new note.

### `apollokairn vocab`

Manages the top-level deterministic glossary.

```bash
apollokairn vocab add-term Kubernetes --alias k8s --alias kube --path ~/brain
apollokairn vocab add-alias Kubernetes kube --path ~/brain
apollokairn vocab add-alias Kubernetes kube --path ~/brain --json
apollokairn vocab suggest "kubernetes rollback" --path ~/brain --limit 5
apollokairn vocab validate --path ~/brain
```

Use this when multiple people or agents describe the same concept with different
terms. Search and retrieval use only `status: approved` terms. Suggestions are
read-only and should be reviewed before adding a new alias.

### `apollokairn stats`

Shows vault size, type/tag distribution, and an approximate token count.

```bash
apollokairn stats --path ~/brain
apollokairn stats --path ~/brain --json
```

Use this to understand whether a vault is growing in a healthy shape.

### `apollokairn export` and `apollokairn import`

Exports or imports a vault zip archive.

```bash
apollokairn export --path ~/brain --output apollokairn-vault.zip
apollokairn import apollokairn-vault.zip --path ~/restored-brain
apollokairn export --path ~/brain --output apollokairn-vault.zip --json
apollokairn import apollokairn-vault.zip --path ~/restored-brain --json
```

Generated index files are not included in exports. Re-run `apollokairn index` after
importing. Export aborts when common secret-like values are detected in files
that would be included in the archive.
JSON output reports the archive `output` path or imported `root` path.

### `apollokairn setup-agent` and `apollokairn refresh-guides`

Creates or refreshes agent-specific instructions inside the vault.

```bash
apollokairn setup-agent codex --path ~/brain
apollokairn setup-agent claude --path ~/brain
apollokairn setup-agent opencode --path ~/brain
apollokairn setup-agent hermes --path ~/brain
apollokairn setup-agent copilot --path ~/brain
apollokairn refresh-guides --path ~/brain
apollokairn setup-agent codex --path ~/brain --json
apollokairn refresh-guides --path ~/brain --json
```

Use these when a vault should be consumed by different agent harnesses. ApolloKairn is
agent-agnostic by design: generated guides and future plugins are adapters over
the same local Markdown vault, not separate knowledge stores.
Generated guides tell agents to use JSON search, passage retrieval with
`--ranker auto`, `apollokairn vocab suggest` for vocabulary gaps, schema-compatible
types/tags, `--body-file` or `--body-stdin` for multi-line Markdown, and
`validate` plus `index` after every successful write.
JSON output reports generated guide paths.
See [Agent adapters](adapters.md) for supported targets and generated paths.

## Recommended Agent Workflow

1. Run `apollokairn doctor --path <vault>`.
2. Run `apollokairn search "<symptom or task>" --path <vault> --json`.
3. Open at most the top three results.
4. Prefer `show --section`, `show --snippet`, or `retrieve --budget` before full
   documents.
5. Solve the task.
6. Run `apollokairn similar "<new knowledge>" --path <vault>`.
7. Update an existing note when possible; create a new note only when the
   knowledge is reusable and not already represented.
8. Run `apollokairn validate --path <vault>` and `apollokairn index --path <vault>`.

## Repository Development

Run tests:

```bash
python -m unittest discover -v
```

Run deterministic evaluations:

```bash
python bench/run_eval.py
python bench/run_eval.py --quiet --compare-golden bench/golden.json
python bench/run_writeback_eval.py --quiet --compare-golden bench/writeback/golden.json
python bench/publish_metrics.py --output docs/data/benchmarks.json --tests 178
```

Benchmark topics may include `category`, `mode`, `compare_mode`, `ranker`, and
`compare_ranker` fields. This lets ApolloKairn measure whether `passages` reduce
returned tokens against `documents`, whether experimental rankers improve
quality against the default `bm25` baseline, and which workflow class each topic
protects. The benchmark output includes a `comparison` summary for
token-reduction comparisons.

The writeback benchmark uses deterministic cases for create, update, no-op,
conflict, duplicate avoidance, and target-path accuracy. It does not call a
model; it exercises ApolloKairn's local similarity and writeback primitives.

`bench/publish_metrics.py` is the publishing step for the GitHub Pages
dashboard. It runs both deterministic suites, updates current metric values,
deduplicates the latest history row by date and label, and adds metric deltas
against the previous run.

The runtime uses only the Python standard library.
