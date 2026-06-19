<div align="center">
  <h1>ApolloKairn</h1>
  <p><strong>Markdown knowledge for search, retrieval, and writeback workflows.</strong></p>
  <p>
    <a href="https://sinkz.github.io/apollokairn/">Website</a> ·
    <a href="docs/guides/quick-install.md">Quick install</a> ·
    <a href="https://sinkz.github.io/apollokairn/learn.html">How it works</a> ·
    <a href="docs/guides/usage.md">Usage guide</a> ·
    <a href="examples/README.md">Examples</a> ·
    <a href="README.pt-BR.md">PT-BR</a>
  </p>
  <p>
    <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white">
    <img alt="Runtime dependencies: zero" src="https://img.shields.io/badge/runtime_dependencies-0-2f6f4e">
    <img alt="Regression tests: 210" src="https://img.shields.io/badge/tests-210-3b6ea8">
    <img alt="Recall at 3: 1.00" src="https://img.shields.io/badge/Recall%403-1.00-2f6f4e">
    <img alt="Context reduction: 91.83%" src="https://img.shields.io/badge/context_reduction-91.83%25-8a5a44">
    <img alt="Writeback decision accuracy: 100%" src="https://img.shields.io/badge/writeback_decisions-100%25-285da8">
    <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-15130f">
  </p>
</div>

## What ApolloKairn Is

ApolloKairn is a local CLI for a Markdown knowledge vault. It helps people and agents
store reusable notes, search them later, retrieve only the context needed for a
task, and write new lessons back to the vault.

The source of truth is plain Markdown with frontmatter. Search is backed by a
local, rebuildable SQLite index. ApolloKairn works best inside agent workflows, but it
does not depend on a specific agent product.

| Area | What it gives you |
| --- | --- |
| Personal notes | Bugs, decisions, references, learning notes, recurring procedures |
| Engineering teams | Runbooks, incidents, library gotchas, architecture decisions |
| Support and product | Access flows, escalation paths, product rules, customer-facing procedures |
| Agent workflows | Search first, retrieve compact context, solve, then update or create notes |

## Current Benchmark Snapshot

The deterministic benchmarks run locally without model calls. They measure
retrieval quality, token budgets, passage-vs-document context reduction, and
writeback decisions for update-vs-create workflows.

| Metric | Current | Meaning |
| --- | ---: | --- |
| Recall@3 | `1.00` | Expected notes appear in the top three results. |
| MRR@3 | `1.00` | Relevant results are ranked first in the current fixture set. |
| nDCG@3 | `0.9941` | Ranking quality against deterministic relevance labels. |
| Context reduction | `91.83%` | Passage retrieval returns far less text than opening full documents. |
| Comparison reduction | `53.73%` | Reduction measured in configured comparison runs. |
| Writeback decision accuracy | `100%` | Correct create, update, no-op, and conflict decisions in the fixture set. |
| Duplicate avoidance | `100%` | Existing reusable notes are updated or preserved instead of duplicated. |
| Regression tests | `210` | Unit and workflow tests run before publishing the current page. |

Benchmark data is also published on the website through
[`docs/data/benchmarks.json`](docs/data/benchmarks.json).

```bash
python bench/run_eval.py --quiet --compare-golden bench/golden.json
python bench/run_writeback_eval.py --quiet --compare-golden bench/writeback/golden.json
python bench/publish_metrics.py --output docs/data/benchmarks.json --tests 210
```

## Quick Install

Prebuilt binaries from GitHub Releases do not require Python.

> ApolloKairn was previously named Cairn. The `cairn` command remains available
> as a compatibility alias for one release, but new docs use `apollokairn`.

Linux and macOS:

```bash
curl -fsSL https://sinkz.github.io/apollokairn/install.sh | sh
```

Windows PowerShell:

```powershell
irm https://sinkz.github.io/apollokairn/install.ps1 | iex
```

Then verify:

```powershell
apollokairn --version
apollokairn --help
```

See [Quick install](docs/guides/quick-install.md) for custom install paths,
version pinning, PATH setup, checksum troubleshooting, and manual fallback.

## Create A Vault

```bash
apollokairn init --path PATH_TO_VAULT --profile engineering
apollokairn validate --path PATH_TO_VAULT
apollokairn index --path PATH_TO_VAULT --rebuild
apollokairn doctor --path PATH_TO_VAULT
```

Profiles create an initial folder structure and schema:

| Profile | Use it for |
| --- | --- |
| `personal` | Personal notes, learning, workflows, references |
| `engineering` | Bugs, runbooks, incidents, libraries, decisions |
| `support` | Support triage, procedures, FAQs, escalations |
| `product` | Requirements, discovery, metrics, release decisions |
| `custom` | A minimal schema you can adapt |

## Register Vaults

Registering vaults lets you work from any repository without remembering long
paths:

```bash
apollokairn vault add PATH_TO_VAULT --name personal --set-active
apollokairn vault list
apollokairn vault current
apollokairn vault use personal
```

Then commands can use the active vault:

```bash
apollokairn search "deploy 403"
apollokairn retrieve "access request" --budget 500
```

Agents and scripts should prefer explicit names after discovery:

```bash
apollokairn vault list --json
apollokairn search "deploy 403" --vault personal --json
```

Vault resolution order is `--path`, then `--vault`, then the active registered
vault, then the current directory for backward compatibility.

## Optional Agent Skill

Install the shared ApolloKairn skill when you want Codex or Hermes to know the
CLI workflow from any repository:

```bash
apollokairn agent install codex
apollokairn agent install hermes
apollokairn agent doctor --json
```

The installer copies a small `apollokairn-vault` skill by default and is safe to
run again. Use `--mode symlink` only when developing from a source checkout.
Vault-local guide files are still available through `apollokairn setup-agent`.

## Install From Source

Source install is mainly useful for development or when release binaries are not
available yet:

```bash
git clone https://github.com/sinkz/apollokairn.git
cd apollokairn
python -m pip install -e .
apollokairn --help
```

Run without installing:

```bash
export PYTHONPATH="$PWD/src"
python -m cairn --help
```

PowerShell:

```powershell
$env:PYTHONPATH = Join-Path (Resolve-Path .).Path "src"
python -m cairn --help
```

## Daily Workflow

### 1. Capture a note

```bash
apollokairn capture --path PATH_TO_VAULT \
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
apollokairn capture --path PATH_TO_VAULT \
  --title "Deploy 403 after token rotation" \
  --description "Fix stale CI authorization after token rotation." \
  --type Runbook \
  --tag bug \
  --tag deploy \
  --body-file PATH_TO_NOTE_BODY.md
```

`capture` and `add` validate the target schema and scan the new content for
common secret-like values before writing the file.

### 2. Search before opening files

```bash
apollokairn index --path PATH_TO_VAULT
apollokairn search "deploy 403 token" --path PATH_TO_VAULT --limit 3
apollokairn search "deploy token rotation kubernetes secret" --path PATH_TO_VAULT --ranker rrf
apollokairn search "deploy 403 token" --path PATH_TO_VAULT --json --explain
```

If your team uses stable synonyms such as `k8s` and `kubernetes`, keep them in
`glossary.md` so search can expand approved vocabulary deterministically:

```bash
apollokairn vocab add-term Kubernetes --alias k8s --alias kube --path PATH_TO_VAULT
apollokairn vocab validate --path PATH_TO_VAULT
apollokairn vocab suggest "kubernetes rollback" --path PATH_TO_VAULT --json
```

### 3. Retrieve compact context

```bash
apollokairn retrieve "deploy 403 token" --path PATH_TO_VAULT --budget 800
apollokairn retrieve "deploy 403 token" --path PATH_TO_VAULT --mode passages --budget 400
apollokairn retrieve "deploy token rotation kubernetes secret" --path PATH_TO_VAULT --ranker auto --budget 800
apollokairn retrieve "deploy 403 token" --path PATH_TO_VAULT --mode passages --budget 400 --json
apollokairn retrieve "deploy 403 token" --path PATH_TO_VAULT --mode passages --budget 400 --json --explain
```

### 4. Update instead of duplicating

```bash
apollokairn similar "deploy forbidden token" --path PATH_TO_VAULT --limit 5

apollokairn update knowledge/deploy-403-after-token-rotation.md \
  --path PATH_TO_VAULT \
  --append "Add the verification step used in the latest incident."
```

For longer updates, use `--append-file PATH_TO_APPEND.md` or pipe content with
`--append-stdin`.
Agents can add `--json`, preview writes with `--dry-run`, and pass
`--expect-sha256 CURRENT_SHA256` to avoid updating a file that changed since it
was inspected. New appended content is scanned for common secret-like values
before it is written.

## Commands

| Command | Purpose |
| --- | --- |
| `apollokairn init` | Create a vault |
| `apollokairn vault` | Register, list, inspect, and switch named vaults |
| `apollokairn validate` | Check frontmatter, schema, and common secret-like values |
| `apollokairn index` | Build or update the local search index |
| `apollokairn doctor` | Check vault and index health |
| `apollokairn capture` / `apollokairn add` | Create a note |
| `apollokairn similar` | Find existing notes before creating a duplicate |
| `apollokairn search` | Return ranked snippets and paths |
| `apollokairn retrieve` | Return context within a token budget |
| `apollokairn show` | Open a full document, section, snippet, or line range |
| `apollokairn update` | Append reusable information to an existing note |
| `apollokairn vocab` | Manage deterministic glossary terms and aliases |
| `apollokairn agent` | Install or check optional Codex/Hermes skills |
| `apollokairn setup-agent` | Create tool-specific instructions such as `CODEX.md`, `HERMES.md`, or Copilot instructions |
| `apollokairn refresh-guides` | Refresh generated agent guides |
| `apollokairn stats` | Show vault counts and approximate token size |
| `apollokairn usage` | Enable local usage metrics and generate a vault report |
| `apollokairn export` / `apollokairn import` | Move a vault as a zip archive |

All operational commands support `--json` for agent workflows; see the
[usage guide](docs/guides/usage.md) for the full contract.

## Example Vault

```bash
apollokairn validate --path examples/engineering-vault
apollokairn index --path examples/engineering-vault --rebuild
apollokairn search "deploy 403 token" --path examples/engineering-vault --limit 3
apollokairn retrieve "hotfix release rollback" --path examples/engineering-vault --mode passages --budget 400
```

See [examples/README.md](examples/README.md) for more walkthroughs.

## Documentation

| Page | Description |
| --- | --- |
| [Website](https://sinkz.github.io/apollokairn/) | Public overview and benchmark cards |
| [How it works](https://sinkz.github.io/apollokairn/learn.html) | Conceptual and technical explanation |
| [Quick install](docs/guides/quick-install.md) | Binary install, PATH setup, and troubleshooting |
| [Usage guide](docs/guides/usage.md) | Full command guide |
| [Agentic assets](agentic/README.md) | Shared Codex/Hermes skill source |
| [Agent adapters](docs/guides/adapters.md) | Generated guides for Codex, Claude, OpenCode, Hermes, Copilot, and generic agents |
| [Example vaults](examples/README.md) | Reproducible examples |
| [Roadmap](ROADMAP.md) | Current implementation phases |
| [Changelog](CHANGELOG.md) | Released changes |
| [Agent instructions](AGENTS.md) | Repository rules for AI agents |
| [PT-BR README](README.pt-BR.md) | Portuguese documentation |

## Development

Run the test suite:

```bash
python -m unittest discover -v
```

Run the deterministic benchmarks:

```bash
python bench/run_eval.py --quiet --compare-golden bench/golden.json
python bench/run_writeback_eval.py --quiet --compare-golden bench/writeback/golden.json
python bench/publish_metrics.py --output docs/data/benchmarks.json --tests 210
```

The benchmarks check ranking quality, golden result prefixes, token budgets,
passage-vs-document context reduction, update-vs-create decisions, no-op
idempotency, duplicate avoidance, and stale-write conflict detection.
`bench/publish_metrics.py` refreshes the public GitHub Pages JSON, deduplicates
the latest history row by date and label, and adds metric deltas against the
previous run.

## OKF Reference

ApolloKairn follows the useful shape of Open Knowledge Format: one concept per
Markdown file, frontmatter metadata, an `index.md`, and a `log.md`. ApolloKairn does
not require Google Cloud, Gemini, BigQuery, or the OKF reference implementation.

- [Google Cloud OKF announcement](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
- [GoogleCloudPlatform/knowledge-catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog)
- [OKF directory](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
- [OKF v0.1 specification](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)

## License

MIT. See [LICENSE](LICENSE).
