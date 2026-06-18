from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


_SLUG_CHARS = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class NoteWriteResult:
    path: str
    changed: bool


def slugify(title: str) -> str:
    slug = _SLUG_CHARS.sub("-", title.casefold()).strip("-")
    return slug or "untitled"


def _frontmatter_list(items: Sequence[str]) -> str:
    return "[" + ", ".join(items) + "]"


def _render_body(body: str) -> str:
    stripped = body.strip()
    if not stripped:
        return "# Context\n\n"
    if stripped.startswith("#"):
        return f"{stripped}\n"
    return f"# Context\n\n{stripped}\n"


def create_note(
    root: Path,
    title: str,
    description: str,
    typ: str = "Note",
    tags: Sequence[str] = (),
    folder: str = "knowledge",
    body: str = "",
    aliases: Sequence[str] = (),
    systems: Sequence[str] = (),
    signals: Sequence[str] = (),
    timestamp: str | None = None,
) -> NoteWriteResult:
    root = Path(root)
    if not title.strip():
        raise ValueError("title is required")
    if not description.strip():
        raise ValueError("description is required")
    timestamp = timestamp or datetime.now(timezone.utc).isoformat()
    rel = Path(folder) / f"{slugify(title)}.md"
    path = (root / rel).resolve()
    if root.resolve() not in path.parents and path != root.resolve():
        raise ValueError("path must stay inside vault")
    if path.exists():
        raise FileExistsError(rel.as_posix())
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "---\n"
        f"type: {typ}\n"
        f"title: {title}\n"
        f"description: {description}\n"
        f"tags: {_frontmatter_list(tags)}\n"
        f"timestamp: {timestamp}\n"
        f"aliases: {_frontmatter_list(aliases)}\n"
        f"systems: {_frontmatter_list(systems)}\n"
        f"signals: {_frontmatter_list(signals)}\n"
        "---\n\n"
        f"{_render_body(body)}"
    )
    path.write_text(content, encoding="utf-8")
    return NoteWriteResult(path=rel.as_posix(), changed=True)


def _resolve_note_path(root: Path, rel_path: str) -> tuple[Path, str]:
    root_resolved = Path(root).resolve()
    candidate = Path(rel_path)
    path = candidate.resolve() if candidate.is_absolute() else (root_resolved / candidate).resolve()
    if root_resolved not in path.parents and path != root_resolved:
        raise ValueError("path must stay inside vault")
    return path, path.relative_to(root_resolved).as_posix()


def _replace_timestamp(text: str, timestamp: str) -> str:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text

    end_index: int | None = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break
    if end_index is None:
        return text

    newline = "\n"
    for line in lines:
        if line.endswith("\r\n"):
            newline = "\r\n"
            break

    for index in range(1, end_index):
        if lines[index].startswith("timestamp:"):
            ending = "\r\n" if lines[index].endswith("\r\n") else "\n" if lines[index].endswith("\n") else ""
            lines[index] = f"timestamp: {timestamp}{ending}"
            return "".join(lines)

    lines.insert(end_index, f"timestamp: {timestamp}{newline}")
    return "".join(lines)


def append_to_note(root: Path, rel_path: str, text: str) -> NoteWriteResult:
    path, display_path = _resolve_note_path(Path(root), rel_path)
    if not path.is_file():
        raise FileNotFoundError(rel_path)
    current = path.read_text(encoding="utf-8")
    snippet = text.strip()
    if not snippet:
        raise ValueError("--append must not be empty")
    if snippet in current:
        return NoteWriteResult(path=display_path, changed=False)
    separator = "\n" if current.endswith("\n") else "\n\n"
    touched = _replace_timestamp(current, datetime.now(timezone.utc).isoformat())
    path.write_text(touched + separator + snippet + "\n", encoding="utf-8")
    return NoteWriteResult(path=display_path, changed=True)
