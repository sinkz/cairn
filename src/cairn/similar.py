from __future__ import annotations

from pathlib import Path
from typing import Sequence

from cairn.indexer import SearchResult, search


def find_similar(
    root: Path,
    query: str,
    limit: int = 5,
    type_filter: str | None = None,
    tag_filters: Sequence[str] = (),
    system_filters: Sequence[str] = (),
) -> list[SearchResult]:
    return search(
        root,
        query,
        limit=limit,
        type_filter=type_filter,
        tag_filters=tag_filters,
        system_filters=system_filters,
    )


def render_similar(results: Sequence[SearchResult]) -> str:
    lines: list[str] = []
    for result in results:
        lines.append(f"possible duplicate: {result.path} :: {result.title}")
        lines.append(result.snippet)
    return "\n".join(lines) + ("\n" if lines else "")
