# Cairn

Cairn is a local CLI for a Markdown knowledge vault. It helps people and AI
agents save reusable notes, search them later, and retrieve only the context
needed for the current task.

Portuguese version: [README.pt-BR.md](README.pt-BR.md)

## What It Does

Cairn is useful when you want to remember things like:

- how a recurring bug was diagnosed and fixed;
- how to request access or run a team process;
- which library, tool, or architecture decision was chosen and why;
- support procedures and product workflows;
- personal notes that should be searchable by an agent later.

The vault is just Markdown files plus frontmatter. The SQLite search index is
local and rebuildable.

## Requirements

- Python 3.11 or newer.
- No runtime Python dependencies outside the standard library.
- Git is optional, but recommended if you want version history for a vault.

## Install From Source

From the repository root:

```bash
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

## Create Your First Vault

Choose where your vault should live, then initialize it:

```bash
cairn init --path PATH_TO_VAULT --profile personal
cairn validate --path PATH_TO_VAULT
cairn index --path PATH_TO_VAULT --rebuild
cairn doctor --path PATH_TO_VAULT
```

Profiles create an initial folder structure and schema:

| Profile | Use it for |
| --- | --- |
| `personal` | personal notes, learning, workflows, references |
| `engineering` | bugs, runbooks, incidents, libraries, decisions |
| `support` | support triage, procedures, FAQs, escalations |
| `product` | requirements, discovery, metrics, release decisions |
| `custom` | a minimal schema you can adapt |

## Add And Search Notes

Create a note:

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

`capture` creates a valid Markdown file with a `# Context` section. For richer
notes, keep the Markdown body in a file and pass it directly:

```bash
cairn capture --path PATH_TO_VAULT \
  --title "Deploy 403 after token rotation" \
  --description "Fix stale CI authorization after token rotation." \
  --type Runbook \
  --tag bug \
  --tag deploy \
  --body-file PATH_TO_NOTE_BODY.md
```

Update the index:

```bash
cairn index --path PATH_TO_VAULT
```

Search before opening full files:

```bash
cairn search "deploy 403 token" --path PATH_TO_VAULT --limit 3
cairn search "deploy token rotation kubernetes secret" --path PATH_TO_VAULT --ranker rrf
```

Retrieve a budgeted context packet for an agent:

```bash
cairn retrieve "deploy 403 token" --path PATH_TO_VAULT --budget 800
cairn retrieve "deploy 403 token" --path PATH_TO_VAULT --mode passages --budget 400
cairn retrieve "deploy token rotation kubernetes secret" --path PATH_TO_VAULT --ranker auto --budget 800
```

Check for an existing note before creating another one:

```bash
cairn similar "deploy forbidden token" --path PATH_TO_VAULT --limit 5
```

If `similar` finds the same topic, update it:

```bash
cairn update knowledge/deploy-403-after-token-rotation.md \
  --path PATH_TO_VAULT \
  --append "Add the verification step used in the latest incident."
```

For longer updates, use `--append-file PATH_TO_APPEND.md` or pipe content with
`--append-stdin`.

## Command Summary

| Command | Purpose |
| --- | --- |
| `cairn init` | create a vault |
| `cairn validate` | check frontmatter, schema, and common secret-like values |
| `cairn index` | build or update the local search index |
| `cairn doctor` | check vault and index health |
| `cairn capture` / `cairn add` | create a note |
| `cairn similar` | find existing notes before creating a duplicate |
| `cairn search` | return ranked snippets and paths |
| `cairn retrieve` | return context within a token budget |
| `cairn show` | open a full document or a section/snippet/line range |
| `cairn update` | append reusable information to an existing note |
| `cairn setup-agent` | create tool-specific instructions such as `CODEX.md` |
| `cairn refresh-guides` | refresh generated agent guides |
| `cairn stats` | show vault counts and approximate token size |
| `cairn export` / `cairn import` | move a vault as a zip archive |

## Try The Example Vault

```bash
cairn validate --path examples/engineering-vault
cairn index --path examples/engineering-vault --rebuild
cairn search "deploy 403 token" --path examples/engineering-vault --limit 3
cairn retrieve "hotfix release rollback" --path examples/engineering-vault --mode passages --budget 400
```

See [examples/README.md](examples/README.md) for more example walkthroughs.

## Documentation

- [Usage guide](docs/guides/usage.md)
- [Guia de uso em PT-BR](docs/guides/usage.pt-BR.md)
- [Example vaults](examples/README.md)
- [Roadmap](ROADMAP.md)
- [Changelog](CHANGELOG.md)

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
