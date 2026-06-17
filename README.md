# Cairn

**Cairn is an agent-ready second brain for people and teams.**

Cairn is a local-first Markdown knowledge vault designed for humans and AI
agents to capture, search, and reuse knowledge without wasting context.

The goal is simple: when a person or an agent solves a problem, makes a
decision, documents a process, or learns a recurring pattern, Cairn helps save
that knowledge in a structured vault so it can be found later by any compatible
agent or editor.

## Why Cairn

Most teams and individuals lose useful knowledge in chat threads, tickets,
temporary notes, and agent sessions. Months later, the same issue appears again
and the discovery work starts from zero.

Cairn turns those solved problems and recurring workflows into a searchable
Markdown vault:

- Local-first: files remain on your machine or in your own Git repository.
- Agent-ready: agents search snippets first and open only the most relevant
  documents.
- Tool-agnostic: the same vault can be used from Codex, Claude Code, OpenCode,
  GitHub Copilot, or any harness that can read files and run a CLI.
- Human-readable: Markdown remains the source of truth.
- OKF-compatible: documents follow the Open Knowledge Format conventions where
  useful, without depending on Google Cloud tooling.

## What OKF Is

Open Knowledge Format (OKF) is a draft open specification introduced by Google
Cloud for representing knowledge as a directory of Markdown files with YAML
frontmatter. Each Markdown file represents one concept, and the file path acts
as the concept identity.

Cairn uses OKF as a lightweight interoperability convention:

- one concept per Markdown file;
- YAML frontmatter for structured metadata such as `type`, `title`,
  `description`, `tags`, and `timestamp`;
- standard Markdown links between concepts;
- `index.md` files for progressive disclosure;
- `log.md` files for chronological updates.

Cairn does not depend on Google Cloud, BigQuery, Gemini, or the OKF reference
implementation. OKF is used as a file-format baseline, while Cairn focuses on
the agent workflow: search first, read only top results, capture after solving,
and avoid duplicate notes.

## Quick Start

From a source checkout, run the CLI with `src` on `PYTHONPATH`.

PowerShell:

```powershell
$repo = (Resolve-Path .).Path
$env:PYTHONPATH = Join-Path $repo "src"
New-Item -ItemType Directory -Force .sandbox/my-vault | Out-Null
python -m cairn init --path .sandbox/my-vault --profile personal
python -m cairn validate --path .sandbox/my-vault
python -m cairn index --path .sandbox/my-vault --rebuild
python -m cairn doctor --path .sandbox/my-vault
python -m cairn search "your query" --path .sandbox/my-vault --limit 3
python -m cairn retrieve "your query" --path .sandbox/my-vault --budget 1000
```

Bash:

```bash
export PYTHONPATH="$PWD/src"
mkdir -p .sandbox/my-vault
python -m cairn init --path .sandbox/my-vault --profile personal
python -m cairn validate --path .sandbox/my-vault
python -m cairn index --path .sandbox/my-vault --rebuild
python -m cairn doctor --path .sandbox/my-vault
python -m cairn search "your query" --path .sandbox/my-vault --limit 3
python -m cairn retrieve "your query" --path .sandbox/my-vault --budget 1000
```

`validate`, `index`, `search`, and `show` can run from outside the vault with
`--path`, which is the preferred mode for agents working across multiple
projects.

`search` and `retrieve` also support metadata filters:

```bash
python -m cairn search "retry timeout" --path .sandbox/my-vault --type Decision --system checkout
python -m cairn retrieve "deploy 403" --path .sandbox/my-vault --tag deploy --budget 800
```

After the first build, `index` is incremental by default:

```bash
python -m cairn index --path .sandbox/my-vault
```

Use `similar` before creating new notes to avoid duplicates:

```bash
python -m cairn similar "deploy forbidden token" --path .sandbox/my-vault --limit 5
```

Use partial `show` when an agent needs less context:

```bash
python -m cairn show knowledge/deploy-403.md --path .sandbox/my-vault --section Diagnosis
python -m cairn show knowledge/deploy-403.md --path .sandbox/my-vault --snippet "workspace access" --context 2
python -m cairn show knowledge/deploy-403.md --path .sandbox/my-vault --lines 20:40
```

The current core runtime uses only the Python standard library.

## References

- Google Cloud announcement: [Introducing the Open Knowledge Format](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
- Google reference repository: [GoogleCloudPlatform/knowledge-catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog)
- OKF directory in the reference repository: [`okf/`](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
- OKF v0.1 specification: [`okf/SPEC.md`](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)

## Project Status

Cairn currently has a Core MVP implemented. Start here:

- [PRD](docs/prd.md)
- [Design](docs/plans/2026-06-17-cairn-design.md)
- [Core MVP implementation plan](docs/superpowers/plans/2026-06-17-cairn-core-mvp.md)
- [OKF research](docs/pesquisa.md)
