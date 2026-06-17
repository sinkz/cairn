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

```bash
cairn validate --path ~/brain
```

Use it before indexing, before committing a vault, or when an agent created or
edited notes.

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
```

Use search before opening full documents. This is the main token-saving command.

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
```

Use this when an agent needs useful context immediately without manually running
`search` and `show`. The budget uses a simple approximation of 4 characters per
token.

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

Finds existing notes before creating a duplicate.

```bash
cairn similar "deploy forbidden token" --path ~/brain --limit 5
```

Use this before adding a new note. If a result is close enough, update the
existing note instead of creating another one.

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

The runtime uses only the Python standard library.
