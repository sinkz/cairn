# Cairn

**Cairn is an agent-ready second brain for people and teams.**

Cairn is a local-first Markdown knowledge vault designed for humans and AI
agents to capture, search, and reuse knowledge without wasting context. It is
tool-agnostic: the same vault can be used from Codex, Claude Code, OpenCode,
GitHub Copilot, or any agent harness that can read files and run a CLI.

Portuguese version: [README.pt-BR.md](README.pt-BR.md)

## Why

Useful knowledge is often lost in chat threads, tickets, terminal sessions, and
agent conversations. Months later, the same bug, process, access issue, or
library decision appears again and the discovery work starts from zero.

Cairn keeps that reusable knowledge in a structured, searchable Markdown vault:

- local-first files you can store in your own Git repository;
- OKF-compatible Markdown/frontmatter conventions;
- fast SQLite FTS search;
- metadata filters and token-budgeted retrieval;
- partial reads so agents open less context;
- duplicate checks before creating new notes.

## Quick Start

```bash
python -m pip install -e .
cairn init --path .sandbox/my-vault --profile personal
cairn validate --path .sandbox/my-vault
cairn index --path .sandbox/my-vault --rebuild
cairn doctor --path .sandbox/my-vault
cairn search "deploy 403" --path .sandbox/my-vault --limit 3
cairn retrieve "deploy 403" --path .sandbox/my-vault --budget 800
```

From a source checkout without installing, set `PYTHONPATH=src` and use
`python -m cairn ...`.

## Documentation

- [English usage guide](docs/guides/usage.md)
- [Guia de uso em PT-BR](docs/guides/usage.pt-BR.md)
- [Product requirements](docs/prd.md)
- [Design notes](docs/plans/2026-06-17-cairn-design.md)
- [OKF research](docs/pesquisa.md)

## OKF Reference

Cairn uses Open Knowledge Format ideas as a lightweight interoperability
baseline. It does not depend on Google Cloud, Gemini, BigQuery, or the OKF
reference implementation.

- [Google Cloud OKF announcement](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
- [GoogleCloudPlatform/knowledge-catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog)
- [OKF directory](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
- [OKF v0.1 specification](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)

## Status

Cairn currently has a working Core MVP plus post-MVP search operations:

- vault initialization profiles;
- validation;
- incremental local index;
- search with filters;
- budgeted retrieval;
- partial document reads;
- similar-note checks;
- vault/index doctor.

The runtime uses only the Python standard library.

## License

MIT. See [LICENSE](LICENSE).
