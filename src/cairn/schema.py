from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CairnSchema:
    profile: str
    types: set[str]
    tags: set[str]


def parse_schema(text: str) -> CairnSchema:
    profile = "custom"
    types: set[str] = set()
    tags: set[str] = set()
    section: str | None = None

    for raw in text.splitlines():
        line = raw.strip()
        profile_match = re.match(r"Profile:\s*`?([^`]+)`?", line)
        if profile_match:
            profile = profile_match.group(1).strip()
            continue
        if line == "## Types":
            section = "types"
            continue
        if line == "## Tags":
            section = "tags"
            continue
        if line.startswith("- ") and section == "types":
            types.add(line[2:].strip())
        elif line.startswith("- ") and section == "tags":
            tags.add(line[2:].strip())

    return CairnSchema(profile=profile, types=types, tags=tags)
