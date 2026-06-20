# ApolloKairn — Claude Code guide

ApolloKairn is a local Markdown knowledge vault ("second brain") with a CLI
(`apollokairn`) for budgeted retrieval, deduplication, and safe writeback. This
file orients Claude Code both for **using** ApolloKairn on a vault and for
**developing** this repository.

## Use ApolloKairn as a tool (recommended setup)

Install the Agent Skill so any Claude Code session learns the CLI workflow:

```bash
apollokairn agent install claude-code      # copies skill to ~/.claude/skills/apollokairn-vault
apollokairn agent doctor claude-code --json
```

The skill (`agentic/skills/apollokairn-vault/SKILL.md`) is the source of truth for
the agent workflow. The short version:

1. Resolve the vault: `apollokairn vault current --json` (or `vault list --json`).
2. Search first: `apollokairn search "<query>" --json --limit 5`.
3. For LLM context, prefer budgeted retrieval over reading whole files:
   `apollokairn retrieve "<query>" --mode passages --ranker auto --budget 800 --json`.
4. If a query returns nothing, say the vault has no matching note — do not invent.
5. Before writing, dedup: `apollokairn similar "<summary>" --json` (check `similarity`/`kind`).
6. Write reusable knowledge with `apollokairn capture` / `add` using `--body-file`
   or `--body-stdin`; only types/tags declared in `SCHEMA.md` are accepted.
7. After writes: `apollokairn validate` then `apollokairn index`.

Every subcommand supports `--help` and `--json`. Use `--path <vault>` or
`--vault <name>`. Never store secrets in notes.

## Develop this repo

```bash
python -m pip install -e .     # editable install
python -m pytest -q            # full suite
apollokairn --help             # 21 subcommands, all self-describing via --help/--json
```

- Core code: `src/cairn/`. Agent assets: `agentic/`. Docs: `docs/guides/`.
- Generated per-vault guides are produced by `apollokairn setup-agent {claude,codex,...}`
  and live inside the vault; see `src/cairn/guides.py`.
- See `AGENTS.md` for the contributor/benchmark workflow and `ROADMAP.md` for
  planned work.
