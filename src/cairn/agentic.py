from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SKILL_NAME = "apollokairn-vault"
SUPPORTED_AGENTS = ("codex", "hermes", "claude-code")
SUPPORTED_MODES = ("copy", "symlink")
SUPPORTED_SCOPES = ("user", "repo")

SKILL_MD = """---
name: apollokairn-vault
description: Use when the user asks to use ApolloKairn, a registered knowledge vault, second brain notes, recurring bug/process memory, or local vault search, retrieval, and writeback.
---

# ApolloKairn Vault

ApolloKairn is a local Markdown knowledge vault. Use the CLI first; avoid reading
the whole vault unless targeted retrieval is not enough.

## Start

1. Check the active vault with `apollokairn vault current --json`.
2. If no active vault exists, run `apollokairn vault list --json` and ask which vault to use.
3. After choosing, pass `--vault NAME` on search, retrieval, and writes.
4. Run `apollokairn doctor --vault NAME` when vault health is unknown.

## Search

- Start with `apollokairn search "<query>" --vault NAME --json --limit 5`.
- For LLM context, use `apollokairn retrieve "<query>" --vault NAME --mode passages --ranker auto --budget 800 --json`.
- If vocabulary may differ, run `apollokairn vocab suggest "<query>" --vault NAME --json`.

## Writeback

- Before creating, run `apollokairn similar "<summary>" --vault NAME --json`.
- Update with `--append-file FILE` or `--append-stdin`; create with `--body-file FILE` or `--body-stdin`.
- After writes, run `apollokairn validate --vault NAME` and `apollokairn index --vault NAME`.

Never store secrets, credentials, tokens, private keys, or passwords.
See `references/commands.md` and `references/workflows.md` for concise recipes.
"""

COMMANDS_MD = """# ApolloKairn Commands

Use `--vault NAME` after selecting a registered vault. Use `--path PATH_TO_VAULT`
only when the vault is not registered.

```bash
apollokairn vault current --json
apollokairn vault list --json
apollokairn vault doctor --json

apollokairn search "deploy 403 token" --vault work --json --limit 5
apollokairn retrieve "deploy 403 token" --vault work --mode passages --ranker auto --budget 800 --json
apollokairn similar "deploy fails after token rotation" --vault work --json

apollokairn update knowledge/deploy-403.md --append-file note.md --vault work
cat note.md | apollokairn update knowledge/deploy-403.md --append-stdin --vault work
apollokairn capture --title "Deploy 403 after token rotation" --description "Fix for CI deploy failures." --type Runbook --tag deploy --body-file note.md --vault work
cat note.md | apollokairn capture --title "Deploy 403 after token rotation" --description "Fix for CI deploy failures." --type Runbook --tag deploy --body-stdin --vault work
apollokairn validate --vault work
apollokairn index --vault work
```
"""

WORKFLOWS_MD = """# ApolloKairn Workflows

## Before answering

1. Resolve the vault with `vault current` or `vault list`.
2. Search first, then retrieve a passage-sized packet.
3. Use the retrieved context as evidence, not as unquestioned truth.
4. If nothing relevant appears, say that the vault had no matching note.

## After solving

1. Summarize the reusable lesson in one or two sentences.
2. Run `similar` with that summary.
3. Update the best matching note when the new lesson belongs there.
4. Create a note only when it is a distinct reusable process, bug, decision, or reference.
5. Validate and index after a successful write.

## Vocabulary mismatch

When a query may use different words than the vault, run `vocab suggest`. Add or
request aliases only when the evidence is clear, such as `k8s` and `kubernetes`.
"""

README_MD = """# ApolloKairn Agentic Assets

This folder contains small, versioned agent instructions for ApolloKairn.

- `skills/apollokairn-vault` is the shared Agent Skill for Codex, Hermes, and Claude Code.
- `apollokairn agent install codex` installs it for Codex.
- `apollokairn agent install hermes` installs it for Hermes.
- `apollokairn agent install claude-code` installs it for Claude Code (`~/.claude/skills`, or `.claude/skills` with `--scope repo`).

The CLI embeds the same skill text so standalone binaries can install it without
needing a source checkout.
"""

ASSET_FILES = {
    "SKILL.md": SKILL_MD,
    "references/commands.md": COMMANDS_MD,
    "references/workflows.md": WORKFLOWS_MD,
}


class AgenticError(ValueError):
    pass


@dataclass(frozen=True)
class AgentInstallResult:
    agent: str
    scope: str
    mode: str
    skill: str
    skills_dir: Path
    path: Path
    changed: bool
    would_change: bool
    message: str


@dataclass(frozen=True)
class AgentDoctorCheck:
    agent: str
    scope: str
    skill: str
    skills_dir: Path
    path: Path
    installed: bool
    mode: str
    message: str


@dataclass(frozen=True)
class AgentDoctorResult:
    ok: bool
    checks: list[AgentDoctorCheck]


def versioned_agentic_root() -> Path:
    return Path(__file__).resolve().parents[2] / "agentic"


def versioned_skill_dir() -> Path:
    return versioned_agentic_root() / "skills" / SKILL_NAME


def default_skills_dir(agent: str, scope: str, repo_path: str | Path | None = None) -> Path:
    agent = _validate_choice(agent, SUPPORTED_AGENTS, "agent")
    scope = _validate_choice(scope, SUPPORTED_SCOPES, "scope")
    if agent == "codex":
        if scope == "repo":
            return Path(repo_path or Path.cwd()).expanduser().resolve() / ".agents" / "skills"
        return Path.home() / ".agents" / "skills"
    if agent == "claude-code":
        if scope == "repo":
            return Path(repo_path or Path.cwd()).expanduser().resolve() / ".claude" / "skills"
        return Path.home() / ".claude" / "skills"
    if scope != "user":
        raise AgenticError("Hermes install currently supports user scope only")
    return Path.home() / ".hermes" / "skills"


def install_agent_skill(
    agent: str,
    *,
    scope: str = "user",
    mode: str = "copy",
    target_dir: str | Path | None = None,
    repo_path: str | Path | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> AgentInstallResult:
    agent = _validate_choice(agent, SUPPORTED_AGENTS, "agent")
    scope = _validate_choice(scope, SUPPORTED_SCOPES, "scope")
    mode = _validate_choice(mode, SUPPORTED_MODES, "mode")
    skills_dir = _skills_dir(agent, scope, target_dir=target_dir, repo_path=repo_path)
    target = skills_dir / SKILL_NAME
    installed = _is_installed(target)
    would_change = not installed or force
    if dry_run:
        return AgentInstallResult(agent, scope, mode, SKILL_NAME, skills_dir, target, False, would_change, "dry run")
    if target.exists() or target.is_symlink():
        if installed and not force:
            return AgentInstallResult(
                agent,
                scope,
                mode,
                SKILL_NAME,
                skills_dir,
                target,
                False,
                False,
                "already installed",
            )
        if not force:
            raise AgenticError(f"skill already exists: {target}; use --force to overwrite")
        _prepare_existing_target(target, mode)
    if mode == "copy":
        _copy_embedded_skill(target)
    else:
        _install_symlink(target)
    return AgentInstallResult(agent, scope, mode, SKILL_NAME, skills_dir, target, True, would_change, "installed")


def doctor_agent_skills(
    agent: str | None = None,
    *,
    scope: str = "user",
    target_dir: str | Path | None = None,
    repo_path: str | Path | None = None,
) -> AgentDoctorResult:
    agents = [agent] if agent else list(SUPPORTED_AGENTS)
    checks = [_doctor_one(item, scope=scope, target_dir=target_dir, repo_path=repo_path) for item in agents]
    return AgentDoctorResult(ok=all(check.installed for check in checks), checks=checks)


def _skills_dir(agent: str, scope: str, target_dir: str | Path | None, repo_path: str | Path | None) -> Path:
    if target_dir is not None:
        return Path(target_dir).expanduser().resolve()
    return default_skills_dir(agent, scope, repo_path=repo_path)


def _validate_choice(value: str, choices: tuple[str, ...], label: str) -> str:
    normalized = value.casefold()
    if normalized not in choices:
        known = ", ".join(choices)
        raise AgenticError(f"unknown {label} '{value}'. Known {label}s: {known}")
    return normalized


def _is_installed(target: Path) -> bool:
    skill_path = target / "SKILL.md"
    if not skill_path.is_file():
        return False
    try:
        text = skill_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return f"name: {SKILL_NAME}" in text


def _copy_embedded_skill(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for relative, text in ASSET_FILES.items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _install_symlink(target: Path) -> None:
    source = versioned_skill_dir()
    if not source.exists():
        raise AgenticError("symlink mode requires a source checkout with agentic/skills/apollokairn-vault")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(source, target_is_directory=True)


def _prepare_existing_target(target: Path, mode: str) -> None:
    if mode == "copy":
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif not target.is_dir():
            raise AgenticError(f"cannot overwrite unsupported target: {target}")
        return
    if target.is_symlink() or target.is_file():
        target.unlink()
        return
    raise AgenticError(f"remove existing directory before symlink install: {target}")


def _doctor_one(
    agent: str,
    *,
    scope: str,
    target_dir: str | Path | None,
    repo_path: str | Path | None,
) -> AgentDoctorCheck:
    agent = _validate_choice(agent, SUPPORTED_AGENTS, "agent")
    skills_dir = _skills_dir(agent, scope, target_dir=target_dir, repo_path=repo_path)
    target = skills_dir / SKILL_NAME
    installed = _is_installed(target)
    if target.is_symlink():
        mode = "symlink"
    elif target.exists():
        mode = "copy"
    else:
        mode = "missing"
    message = "installed" if installed else "not installed"
    return AgentDoctorCheck(agent, scope, SKILL_NAME, skills_dir, target, installed, mode, message)
