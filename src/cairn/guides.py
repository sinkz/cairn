from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


GUIDE_FILES = {
    "agents": "AGENTS.md",
    "codex": "CODEX.md",
    "claude": "CLAUDE.md",
    "copilot": ".github/copilot-instructions.md",
    "hermes": "HERMES.md",
    "opencode": "OPENCODE.md",
}


@dataclass(frozen=True)
class GuideResult:
    path: str


def _guide_name_from_file(path: str) -> str:
    upper = Path(path).name.upper()
    if upper == "CODEX.MD":
        return "Codex"
    if upper == "CLAUDE.MD":
        return "Claude"
    if upper == "COPILOT-INSTRUCTIONS.MD":
        return "GitHub Copilot"
    if upper == "HERMES.MD":
        return "Hermes"
    if upper == "OPENCODE.MD":
        return "OpenCode"
    return "Agents"


def _guide_path(root: Path, filename: str) -> Path:
    path = root / filename
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("guide path must stay inside vault") from exc
    return path


def render_agent_guide(name: str = "Agents") -> str:
    return (
        f"# ApolloKairn Guide for {name}\n\n"
        "Use ApolloKairn as the local knowledge source before solving recurring work.\n\n"
        "## Before Answering\n\n"
        "1. Resolve the vault with `apollokairn vault current --json`, `apollokairn vault list --json`, `--vault <name>`, or `--path <vault>`.\n"
        "2. Run `apollokairn doctor --vault <name>` or `apollokairn doctor --path <vault>` when vault health is unknown.\n"
        "3. Run `apollokairn search \"<query>\" --vault <name> --json` or `apollokairn search \"<query>\" --path <vault> --json` for saved knowledge.\n"
        "4. Open at most the top 3 relevant documents.\n"
        "5. Prefer `apollokairn retrieve \"<query>\" --vault <name> --mode passages --ranker auto --budget 800 --json` or partial `apollokairn show` before reading full files.\n"
        "6. When query vocabulary may differ, run `apollokairn vocab suggest \"<query>\" --vault <name> --json` before adding aliases.\n\n"
        "## After Solving\n\n"
        "1. Run `apollokairn similar \"<new knowledge>\" --vault <name>` or `apollokairn similar \"<new knowledge>\" --path <vault>`.\n"
        "2. Prefer `apollokairn update <path> --append \"<note>\" --vault <name>` when a related note exists.\n"
        "3. Use `apollokairn add` or `apollokairn capture` only for reusable knowledge that is not already represented.\n"
        "4. Use only types and tags declared in `SCHEMA.md`; ApolloKairn rejects invalid writes before creating files.\n"
        "5. Use `--body-file` or `--body-stdin` for multi-line Markdown instead of shell-escaped `\\n` text.\n"
        "6. Run `apollokairn validate --path <vault>` and `apollokairn index --path <vault>` after every successful write.\n\n"
        "Never store secrets, credentials, tokens, private keys, or passwords.\n"
    )


def setup_agent(root: Path, agent: str) -> GuideResult:
    root = Path(root)
    key = agent.casefold()
    if key not in GUIDE_FILES:
        known = ", ".join(sorted(GUIDE_FILES))
        raise ValueError(f"unknown agent '{agent}'. Known agents: {known}")
    filename = GUIDE_FILES[key]
    path = _guide_path(root, filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_agent_guide(_guide_name_from_file(filename)), encoding="utf-8")
    return GuideResult(path=filename)


def refresh_guides(root: Path) -> list[GuideResult]:
    root = Path(root)
    config_path = root / ".cairn" / "config.json"
    guide_files = ["AGENTS.md"]
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            configured = data.get("generated_guides", guide_files)
            if isinstance(configured, list):
                guide_files = [item for item in configured if isinstance(item, str)]
        except json.JSONDecodeError:
            pass
    results: list[GuideResult] = []
    for filename in guide_files:
        path = _guide_path(root, filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_agent_guide(_guide_name_from_file(filename)), encoding="utf-8")
        results.append(GuideResult(path=filename))
    return results
