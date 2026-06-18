# Cairn Usage Guide

This guide explains what Cairn is for, how to configure a vault, and when to use
each command.

## What Cairn Is For

Cairn is a local Markdown knowledge vault optimized for AI agents and humans.
It helps you save reusable knowledge after solving problems, making decisions,
documenting processes, or learning recurring patterns.

Typical use cases:

- debugging notes and recurring bug fixes;
- operational runbooks;
- support escalation procedures;
- product or architecture decisions;
- library references and access/process notes;
- personal notes that should be searchable by an agent later.

The core idea is simple: agents should search first, open only the most relevant
documents, and write back reusable knowledge after the work is solved.

## Installation

For local development:

```bash
python -m pip install -e .
```

From a source checkout without installing:

```bash
export PYTHONPATH="$PWD/src"
python -m cairn --help
```

PowerShell:

```powershell
$env:PYTHONPATH = Join-Path (Resolve-Path .).Path "src"
python -m cairn --help
```

## Creating a Vault

```bash
cairn init --path ~/brain --profile personal
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
| `.cairn/config.json` | Cairn settings |
| `_templates/concept.md` | Starting template for new notes |
| domain folders | `knowledge`, `processes`, `decisions`, `references`, `notes`, `inbox` |

## Configuration

Cairn stores local settings in `.cairn/config.json`.

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
| `generated_guides` | Agent guide files managed by Cairn |

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

## Command Reference

### `cairn init`

Creates a new vault.

```bash
cairn init --path ~/brain --profile engineering
```

Use this once per vault. Running it again is safe; existing files are skipped.

### `cairn validate`

Checks whether Markdown notes follow `SCHEMA.md` and required frontmatter rules.
It also blocks common secret-like values such as access keys, provider tokens,
and private key blocks without printing the detected value.

```bash
cairn validate --path ~/brain
```

Use it before indexing, before committing a vault, or when an agent created or
edited notes.

### `cairn add` and `cairn capture`

Creates a reusable note with valid Cairn frontmatter.

```bash
cairn add --path ~/brain \
  --title "Deploy 403 after token rotation" \
  --description "Fixes stale CI authorization after token rotation." \
  --type Runbook \
  --tag bug \
  --tag deploy \
  --system ci \
  --signal "HTTP 403" \
  --body "# Context\n\nDeploy failed after token rotation."
```

`capture` is an alias with the same behavior. Use these after a task is solved
and the knowledge is likely to be useful again.

### `cairn update`

Appends text to an existing note if the same text is not already present.

```bash
cairn update knowledge/deploy-403.md --path ~/brain --append "Add the new verification step."
```

Use it when `cairn similar` finds an existing note that should be expanded
instead of duplicated.

### `cairn index`

Builds or updates the local SQLite FTS index.

```bash
cairn index --path ~/brain --rebuild
cairn index --path ~/brain
```

Use `--rebuild` after the first setup or if the index is corrupted. Without
`--rebuild`, indexing is incremental: changed files are updated, removed files
are deleted from the index, and unchanged files are skipped.

### `cairn doctor`

Checks vault health and index freshness.

```bash
cairn doctor --path ~/brain
```

Use it when search behaves oddly, after manual file edits, or before an agent
session starts. It reports validation errors, missing index, invalid index, or
stale index metadata.

### `cairn search`

Searches the vault and returns compact results with snippets.

```bash
cairn search "deploy 403 workspace access" --path ~/brain --limit 3
cairn search "deploy token rotation kubernetes secret" --path ~/brain --ranker rrf
```

Use search before opening full documents. This is the main token-saving command.
The default `bm25` ranker is strict and stable. Use experimental `--ranker rrf`
when the query may contain extra terms or lexical variants and you want Cairn to
fuse multiple cheap lexical runs.

Filters:

```bash
cairn search "retry timeout" --path ~/brain --type Decision
cairn search "deploy" --path ~/brain --tag deploy
cairn search "timeout" --path ~/brain --system checkout
```

JSON output for agents:

```bash
cairn search "cache stampede" --path ~/brain --json
```

### `cairn retrieve`

Builds a context packet for an LLM under an approximate token budget.

```bash
cairn retrieve "deploy 403" --path ~/brain --limit 3 --budget 800
cairn retrieve "deploy 403" --path ~/brain --mode passages --budget 500
cairn retrieve "deploy token rotation kubernetes secret" --path ~/brain --ranker rrf --budget 800
cairn retrieve "reconnecting cache workers" --path ~/brain --mode passages --ranker rrf --budget 500
```

Use this when an agent needs useful context immediately without manually running
`search` and `show`. The budget uses a simple approximation of 4 characters per
token. Retrieval redacts common secret-like values before printing the context
packet.

Use `--mode passages` when the agent needs the smallest useful sections instead
of full matching documents. Passage output includes the source path, heading,
and line range so the agent can reopen the exact context if needed.

Use `--ranker rrf` with documents or passages when the strict default search
returns nothing because the query mixes correct signals with extra terms or
safe lexical variants. RRF stays opt-in; the default `bm25` path remains strict.

Filters work the same way as `search`:

```bash
cairn retrieve "retry timeout" --path ~/brain --type Decision --system checkout --budget 600
```

### `cairn show`

Opens a document from the vault.

```bash
cairn show knowledge/deploy-403.md --path ~/brain
```

Use partial reads to reduce context:

```bash
cairn show knowledge/deploy-403.md --path ~/brain --section Diagnosis
cairn show knowledge/deploy-403.md --path ~/brain --snippet "workspace access" --context 2
cairn show knowledge/deploy-403.md --path ~/brain --lines 20:40
```

Partial reads are useful after `search` identifies the right document but the
agent only needs one section or nearby lines.

### `cairn similar`

Finds existing notes before creating a duplicate. It combines indexed lexical
search with a lightweight local fingerprint scan, so it can still catch near
duplicates when the new note contains extra terms.

```bash
cairn similar "deploy forbidden token" --path ~/brain --limit 5
```

Use this before adding a new note. If a result is close enough, update the
existing note instead of creating another one.

JSON output is available for agents:

```bash
cairn similar "deploy forbidden token" --path ~/brain --json
```

### `cairn stats`

Shows vault size, type/tag distribution, and an approximate token count.

```bash
cairn stats --path ~/brain
cairn stats --path ~/brain --json
```

Use this to understand whether a vault is growing in a healthy shape.

### `cairn export` and `cairn import`

Exports or imports a vault zip archive.

```bash
cairn export --path ~/brain --output cairn-vault.zip
cairn import cairn-vault.zip --path ~/restored-brain
```

Generated index files are not included in exports. Re-run `cairn index` after
importing. Export aborts when common secret-like values are detected in files
that would be included in the archive.

### `cairn setup-agent` and `cairn refresh-guides`

Creates or refreshes agent-specific instructions inside the vault.

```bash
cairn setup-agent codex --path ~/brain
cairn setup-agent claude --path ~/brain
cairn setup-agent opencode --path ~/brain
cairn refresh-guides --path ~/brain
```

Use these when a vault should be consumed by different agent harnesses. Cairn
keeps Markdown as the source of truth; plugins can come later as thin adapters.

## Recommended Agent Workflow

1. Run `cairn doctor --path <vault>`.
2. Run `cairn search "<symptom or task>" --path <vault> --json`.
3. Open at most the top three results.
4. Prefer `show --section`, `show --snippet`, or `retrieve --budget` before full
   documents.
5. Solve the task.
6. Run `cairn similar "<new knowledge>" --path <vault>`.
7. Update an existing note when possible; create a new note only when the
   knowledge is reusable and not already represented.
8. Run `cairn validate --path <vault>` and `cairn index --path <vault>`.

## Repository Development

Run tests:

```bash
python -m unittest discover -v
```

Run deterministic search evaluation:

```bash
python bench/run_eval.py
python bench/run_eval.py --quiet --compare-golden bench/golden.json
```

Benchmark topics may include `category`, `mode`, `compare_mode`, `ranker`, and
`compare_ranker` fields. This lets Cairn measure whether `passages` reduce
returned tokens against `documents`, whether experimental rankers improve
quality against the default `bm25` baseline, and which workflow class each topic
protects. The benchmark output includes a `comparison` summary for
token-reduction comparisons.

The runtime uses only the Python standard library.
