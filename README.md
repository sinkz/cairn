<div align="center">
  <h1>Cairn</h1>
  <p><strong>Markdown knowledge for search, retrieval, and writeback workflows.</strong></p>
  <p>
    <a href="https://sinkz.github.io/cairn/">Website</a> ·
    <a href="https://sinkz.github.io/cairn/learn.html">How it works</a> ·
    <a href="docs/guides/usage.md">Usage guide</a> ·
    <a href="examples/README.md">Examples</a> ·
    <a href="README.pt-BR.md">PT-BR</a>
  </p>
  <p>
    <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white">
    <img alt="Runtime dependencies: zero" src="https://img.shields.io/badge/runtime_dependencies-0-2f6f4e">
    <img alt="Regression tests: 111" src="https://img.shields.io/badge/tests-111-3b6ea8">
    <img alt="Recall at 3: 1.00" src="https://img.shields.io/badge/Recall%403-1.00-2f6f4e">
    <img alt="Context reduction: 92.16%" src="https://img.shields.io/badge/context_reduction-92.16%25-8a5a44">
    <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-15130f">
  </p>
</div>

## What Cairn Is

Cairn is a local CLI for a Markdown knowledge vault. It helps people and agents
store reusable notes, search them later, retrieve only the context needed for a
task, and write new lessons back to the vault.

The source of truth is plain Markdown with frontmatter. Search is backed by a
local, rebuildable SQLite index. Cairn works best inside agent workflows, but it
does not depend on a specific agent product.

| Area | What it gives you |
| --- | --- |
| Personal notes | Bugs, decisions, references, learning notes, recurring procedures |
| Engineering teams | Runbooks, incidents, library gotchas, architecture decisions |
| Support and product | Access flows, escalation paths, product rules, customer-facing procedures |
| Agent workflows | Search first, retrieve compact context, solve, then update or create notes |

## Current Benchmark Snapshot

The deterministic benchmark runs locally without model calls. It measures
ranking quality, token budgets, and passage-vs-document context reduction.

| Metric | Current | Meaning |
| --- | ---: | --- |
| Recall@3 | `1.00` | Expected notes appear in the top three results. |
| MRR@3 | `1.00` | Relevant results are ranked first in the current fixture set. |
| nDCG@3 | `0.9931` | Ranking quality against deterministic relevance labels. |
| Context reduction | `92.16%` | Passage retrieval returns far less text than opening full documents. |
| Comparison reduction | `53.73%` | Reduction measured in configured comparison runs. |
| Regression tests | `111` | Unit and workflow tests run before publishing the current page. |

Benchmark data is also published on the website through
[`docs/data/benchmarks.json`](docs/data/benchmarks.json).

```bash
python bench/run_eval.py --quiet --compare-golden bench/golden.json
```

## Quick Start

```bash
git clone https://github.com/sinkz/cairn.git
cd cairn
python -m pip install -e .
cairn --help
```

If you do not want to install the package, run it from the source checkout:

```bash
export PYTHONPATH="$PWD/src"
python -m cairn --help
```

PowerShell:

```powershell
$env:PYTHONPATH = Join-Path (Resolve-Path .).Path "src"
python -m cairn --help
```

## Create A Vault

```bash
cairn init --path PATH_TO_VAULT --profile personal
cairn validate --path PATH_TO_VAULT
cairn index --path PATH_TO_VAULT --rebuild
cairn doctor --path PATH_TO_VAULT
```

Profiles create an initial folder structure and schema:

| Profile | Use it for |
| --- | --- |
| `personal` | Personal notes, learning, workflows, references |
| `engineering` | Bugs, runbooks, incidents, libraries, decisions |
| `support` | Support triage, procedures, FAQs, escalations |
| `product` | Requirements, discovery, metrics, release decisions |
| `custom` | A minimal schema you can adapt |

## Daily Workflow

### 1. Capture a note

```bash
cairn capture --path PATH_TO_VAULT \
  --title "Deploy 403 after token rotation" \
  --description "Fix stale CI authorization after token rotation." \
  --type Runbook \
  --tag bug \
  --tag deploy \
  --system ci \
  --signal "HTTP 403" \
  --body "Deploy failed after a token rotation. Update the CI secret and rerun the failed job."
```

For larger notes, keep the body in a Markdown file:

```bash
cairn capture --path PATH_TO_VAULT \
  --title "Deploy 403 after token rotation" \
  --description "Fix stale CI authorization after token rotation." \
  --type Runbook \
  --tag bug \
  --tag deploy \
  --body-file PATH_TO_NOTE_BODY.md
```

### 2. Search before opening files

```bash
cairn index --path PATH_TO_VAULT
cairn search "deploy 403 token" --path PATH_TO_VAULT --limit 3
cairn search "deploy token rotation kubernetes secret" --path PATH_TO_VAULT --ranker rrf
```

### 3. Retrieve compact context

```bash
cairn retrieve "deploy 403 token" --path PATH_TO_VAULT --budget 800
cairn retrieve "deploy 403 token" --path PATH_TO_VAULT --mode passages --budget 400
cairn retrieve "deploy token rotation kubernetes secret" --path PATH_TO_VAULT --ranker auto --budget 800
```

### 4. Update instead of duplicating

```bash
cairn similar "deploy forbidden token" --path PATH_TO_VAULT --limit 5

cairn update knowledge/deploy-403-after-token-rotation.md \
  --path PATH_TO_VAULT \
  --append "Add the verification step used in the latest incident."
```

For longer updates, use `--append-file PATH_TO_APPEND.md` or pipe content with
`--append-stdin`.

## Commands

| Command | Purpose |
| --- | --- |
| `cairn init` | Create a vault |
| `cairn validate` | Check frontmatter, schema, and common secret-like values |
| `cairn index` | Build or update the local search index |
| `cairn doctor` | Check vault and index health |
| `cairn capture` / `cairn add` | Create a note |
| `cairn similar` | Find existing notes before creating a duplicate |
| `cairn search` | Return ranked snippets and paths |
| `cairn retrieve` | Return context within a token budget |
| `cairn show` | Open a full document, section, snippet, or line range |
| `cairn update` | Append reusable information to an existing note |
| `cairn setup-agent` | Create tool-specific instructions such as `CODEX.md` |
| `cairn refresh-guides` | Refresh generated agent guides |
| `cairn stats` | Show vault counts and approximate token size |
| `cairn export` / `cairn import` | Move a vault as a zip archive |

## Example Vault

```bash
cairn validate --path examples/engineering-vault
cairn index --path examples/engineering-vault --rebuild
cairn search "deploy 403 token" --path examples/engineering-vault --limit 3
cairn retrieve "hotfix release rollback" --path examples/engineering-vault --mode passages --budget 400
```

See [examples/README.md](examples/README.md) for more walkthroughs.

## Documentation

| Page | Description |
| --- | --- |
| [Website](https://sinkz.github.io/cairn/) | Public overview and benchmark cards |
| [How it works](https://sinkz.github.io/cairn/learn.html) | Conceptual and technical explanation |
| [Usage guide](docs/guides/usage.md) | Full command guide |
| [Example vaults](examples/README.md) | Reproducible examples |
| [Roadmap](ROADMAP.md) | Current implementation phases |
| [Changelog](CHANGELOG.md) | Released changes |
| [PT-BR README](README.pt-BR.md) | Portuguese documentation |

## Development

Run the test suite:

```bash
python -m unittest discover -v
```

Run the deterministic search benchmark:

```bash
python bench/run_eval.py --quiet --compare-golden bench/golden.json
```

The benchmark checks ranking quality, golden result prefixes, token budgets, and
passage-vs-document context reduction.

## OKF Reference

Cairn follows the useful shape of Open Knowledge Format: one concept per
Markdown file, frontmatter metadata, an `index.md`, and a `log.md`. Cairn does
not require Google Cloud, Gemini, BigQuery, or the OKF reference implementation.

- [Google Cloud OKF announcement](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
- [GoogleCloudPlatform/knowledge-catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog)
- [OKF directory](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
- [OKF v0.1 specification](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)

## License

MIT. See [LICENSE](LICENSE).
