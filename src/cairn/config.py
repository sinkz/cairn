from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CairnConfig:
    exclude: tuple[str, ...] = ()


def load_config(root: Path) -> CairnConfig:
    path = Path(root) / ".cairn" / "config.json"
    if not path.exists():
        return CairnConfig()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return CairnConfig()
    exclude = data.get("exclude", [])
    if not isinstance(exclude, list):
        return CairnConfig()
    return CairnConfig(
        exclude=tuple(item for item in exclude if isinstance(item, str) and item.strip())
    )


def is_excluded(root: Path, path: Path, config: CairnConfig | None = None) -> bool:
    root = Path(root)
    config = load_config(root) if config is None else config
    rel = path.relative_to(root).as_posix()
    parts = rel.split("/")
    for raw_pattern in config.exclude:
        pattern = raw_pattern.strip().replace("\\", "/").strip("/")
        if not pattern:
            continue
        if rel == pattern or rel.startswith(pattern + "/"):
            return True
        if pattern in parts:
            return True
        if fnmatch.fnmatch(rel, pattern) or any(fnmatch.fnmatch(part, pattern) for part in parts):
            return True
    return False
