from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from cairn.profiles import get_profile
from cairn.templates import render_agents_md, render_concept_template, render_schema_md


@dataclass
class InitResult:
    root: Path
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def _write_if_missing(path: Path, text: str, result: InitResult) -> None:
    rel = path.relative_to(result.root).as_posix()
    if path.exists():
        result.skipped.append(rel)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    result.created.append(rel)


def init_vault(root: Path, profile_name: str = "personal") -> InitResult:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    profile = get_profile(profile_name)
    result = InitResult(root=root)

    config = {
        "profile": profile.name,
        "search_limit": 3,
        "exclude": ["inbox"],
        "generated_guides": ["AGENTS.md"],
    }

    _write_if_missing(root / "AGENTS.md", render_agents_md(profile), result)
    _write_if_missing(root / "SCHEMA.md", render_schema_md(profile), result)
    _write_if_missing(root / "index.md", "# Cairn Vault\n\n", result)
    _write_if_missing(root / "log.md", "# Cairn Update Log\n\n", result)
    _write_if_missing(root / ".gitignore", ".cairn/index.db\n", result)
    _write_if_missing(
        root / ".cairn" / "config.json",
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        result,
    )
    _write_if_missing(
        root / "_templates" / "concept.md",
        render_concept_template(profile.types[0]),
        result,
    )

    for folder in profile.folders:
        path = root / folder
        rel = path.relative_to(root).as_posix()
        if path.exists():
            result.skipped.append(rel)
        else:
            path.mkdir(parents=True)
            result.created.append(rel)

    return result
