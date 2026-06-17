from __future__ import annotations

import re


_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def extract_lines(text: str, spec: str) -> str:
    if ":" not in spec:
        raise ValueError("--lines must use START:END")
    start_text, end_text = spec.split(":", 1)
    try:
        start = int(start_text)
        end = int(end_text)
    except ValueError as exc:
        raise ValueError("--lines must use numeric START:END") from exc
    if start <= 0 or end < start:
        raise ValueError("--lines must use a positive START:END range")
    lines = text.splitlines(keepends=True)
    return "".join(lines[start - 1 : end])


def extract_section(text: str, name: str) -> str:
    lines = text.splitlines(keepends=True)
    section_start: int | None = None
    section_level: int | None = None
    target = name.strip().casefold()
    for index, line in enumerate(lines):
        match = _HEADING.match(line.rstrip("\n"))
        if not match:
            continue
        level = len(match.group(1))
        heading = match.group(2).strip().casefold()
        if section_start is None and heading == target:
            section_start = index
            section_level = level
            continue
        if section_start is not None and section_level is not None and level <= section_level:
            return "".join(lines[section_start:index])
    if section_start is None:
        raise ValueError(f"section not found: {name}")
    return "".join(lines[section_start:])


def extract_snippet(text: str, query: str, context: int = 2) -> str:
    if context < 0:
        raise ValueError("--context must be non-negative")
    needle = query.casefold()
    if not needle:
        raise ValueError("--snippet must not be empty")
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if needle in line.casefold():
            start = max(index - context, 0)
            end = min(index + context + 1, len(lines))
            return "".join(lines[start:end])
    raise ValueError(f"snippet not found: {query}")
