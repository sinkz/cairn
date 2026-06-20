# ApolloKairn Agentic Assets

This folder contains small, versioned agent instructions for ApolloKairn.

- `skills/apollokairn-vault` is the shared Agent Skill for Codex, Hermes, and Claude Code.
- `apollokairn agent install codex` installs it for Codex.
- `apollokairn agent install hermes` installs it for Hermes.
- `apollokairn agent install claude-code` installs it for Claude Code (`~/.claude/skills`, or `.claude/skills` with `--scope repo`).

The CLI embeds the same skill text so standalone binaries can install it without
needing a source checkout.
