from __future__ import annotations

import math
from pathlib import Path
from typing import Sequence

from cairn.indexer import search, search_passages, show
from cairn.secret_scan import redact_text


CHARS_PER_TOKEN = 4


def approx_tokens(text: str) -> int:
    return math.ceil(len(text) / CHARS_PER_TOKEN)


def _fit(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    suffix = "\n[truncated]\n"
    if max_chars <= len(suffix):
        return text[:max_chars]
    return text[: max_chars - len(suffix)].rstrip() + suffix


def retrieve(
    root: Path,
    query: str,
    limit: int = 3,
    budget_tokens: int = 1000,
    mode: str = "documents",
    type_filter: str | None = None,
    tag_filters: Sequence[str] = (),
    system_filters: Sequence[str] = (),
    ranker: str = "bm25",
) -> str:
    if limit <= 0:
        raise ValueError("limit must be positive")
    if budget_tokens <= 0:
        raise ValueError("budget must be positive")
    if mode not in {"documents", "passages"}:
        raise ValueError("mode must be 'documents' or 'passages'")
    if ranker not in {"bm25", "rrf"}:
        raise ValueError("ranker must be 'bm25' or 'rrf'")

    max_chars = budget_tokens * CHARS_PER_TOKEN
    parts: list[str] = []
    used_chars = 0

    if mode == "passages":
        for result in search_passages(
            root,
            query,
            limit=limit,
            type_filter=type_filter,
            tag_filters=tag_filters,
            system_filters=system_filters,
            ranker=ranker,
        ):
            prefix = (
                f"path: {result.path}\n"
                f"title: {result.title}\n"
                f"type: {result.type}\n"
                f"tags: {', '.join(result.tags)}\n"
                f"heading: {result.heading}\n"
                f"lines: {result.start_line}:{result.end_line}\n"
                f"snippet: {result.snippet}\n"
                "content:\n"
            )
            separator = "\n---\n" if parts else ""
            remaining = max_chars - used_chars - len(separator) - len(prefix)
            if remaining <= 0:
                break
            content = _fit(result.text, remaining)
            block = redact_text(separator + prefix + content)
            parts.append(block)
            used_chars += len(block)
            if used_chars >= max_chars or len(content) < remaining:
                continue
            break
        return "".join(parts)

    for result in search(
        root,
        query,
        limit=limit,
        type_filter=type_filter,
        tag_filters=tag_filters,
        system_filters=system_filters,
        ranker=ranker,
    ):
        prefix = (
            f"path: {result.path}\n"
            f"title: {result.title}\n"
            f"type: {result.type}\n"
            f"tags: {', '.join(result.tags)}\n"
            f"snippet: {result.snippet}\n"
            "content:\n"
        )
        separator = "\n---\n" if parts else ""
        remaining = max_chars - used_chars - len(separator) - len(prefix)
        if remaining <= 0:
            break
        content = _fit(show(root, result.path), remaining)
        block = redact_text(separator + prefix + content)
        parts.append(block)
        used_chars += len(block)
        if used_chars >= max_chars or len(content) < remaining:
            continue
        break

    return "".join(parts)
