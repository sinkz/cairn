from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from cairn.config import is_excluded, load_config
from cairn.fingerprints import fingerprint_similarity
from cairn.frontmatter import FrontmatterError, parse_document
from cairn.indexer import SearchResult, search, show
from cairn.validate import RESERVED_NAMES


_TOKEN = re.compile(r"\w+", re.UNICODE)
_FINGERPRINT_THRESHOLD = 0.55
_DUPLICATE_THRESHOLD = 0.8


@dataclass(frozen=True)
class SimilarResult:
    path: str
    title: str
    type: str
    tags: list[str]
    score: float
    snippet: str
    similarity: float
    kind: str


def _tokens(text: str) -> set[str]:
    return {token.casefold() for token in _TOKEN.findall(text)}


def lexical_similarity(query: str, text: str) -> float:
    query_tokens = _tokens(query)
    text_tokens = _tokens(text)
    if not query_tokens or not text_tokens:
        return 0.0
    overlap = len(query_tokens & text_tokens)
    return overlap / len(query_tokens)


def similar_kind(similarity: float) -> str:
    return "duplicate_candidate" if similarity >= _DUPLICATE_THRESHOLD else "related"


def _as_text(value: object) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return "" if value is None else str(value)


def _casefold_items(items: Sequence[str]) -> set[str]:
    return {item.casefold() for item in items if item}


def _matches_filters(
    typ: str,
    tags: Sequence[str],
    systems: Sequence[str],
    type_filter: str | None,
    tag_filters: Sequence[str],
    system_filters: Sequence[str],
) -> bool:
    if type_filter and typ.casefold() != type_filter.casefold():
        return False
    tag_set = _casefold_items(tags)
    if any(tag.casefold() not in tag_set for tag in tag_filters):
        return False
    system_set = _casefold_items(systems)
    if any(system.casefold() not in system_set for system in system_filters):
        return False
    return True


def _concept_files(root: Path) -> list[Path]:
    ignored_parts = {".cairn", "_templates"}
    config = load_config(root)
    out: list[Path] = []
    for path in root.rglob("*.md"):
        if path.name in RESERVED_NAMES:
            continue
        if any(part in ignored_parts for part in path.relative_to(root).parts):
            continue
        if is_excluded(root, path, config):
            continue
        out.append(path)
    return sorted(out)


def _document_candidates(
    root: Path,
    query: str,
    type_filter: str | None,
    tag_filters: Sequence[str],
    system_filters: Sequence[str],
) -> list[SimilarResult]:
    out: list[SimilarResult] = []
    for path in _concept_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            raw = path.read_text(encoding="utf-8")
            parsed = parse_document(raw)
        except (OSError, FrontmatterError):
            continue
        fm = parsed.frontmatter
        typ = _as_text(fm.get("type"))
        title = _as_text(fm.get("title"))
        tags = [tag for tag in _as_text(fm.get("tags")).split() if tag]
        systems = [system for system in _as_text(fm.get("systems")).split() if system]
        if not _matches_filters(typ, tags, systems, type_filter, tag_filters, system_filters):
            continue
        match_text = "\n".join(
            [
                title,
                _as_text(fm.get("description")),
                _as_text(fm.get("aliases")),
                _as_text(fm.get("signals")),
                parsed.body,
            ]
        )
        similarity = max(
            lexical_similarity(query, match_text),
            fingerprint_similarity(query, match_text),
        )
        if similarity < _FINGERPRINT_THRESHOLD:
            continue
        snippet = " ".join(parsed.body.split())[:160]
        out.append(
            SimilarResult(
                path=rel,
                title=title,
                type=typ,
                tags=tags,
                score=0.0,
                snippet=snippet,
                similarity=round(similarity, 4),
                kind=similar_kind(similarity),
            )
        )
    return out


def find_similar(
    root: Path,
    query: str,
    limit: int = 5,
    type_filter: str | None = None,
    tag_filters: Sequence[str] = (),
    system_filters: Sequence[str] = (),
) -> list[SimilarResult]:
    results = search(
        root,
        query,
        limit=limit,
        type_filter=type_filter,
        tag_filters=tag_filters,
        system_filters=system_filters,
    )
    by_path: dict[str, SimilarResult] = {}
    for result in results:
        try:
            text = show(root, result.path)
        except (FileNotFoundError, ValueError):
            text = result.title + "\n" + result.snippet
        similarity = max(lexical_similarity(query, text), fingerprint_similarity(query, text))
        by_path[result.path] = SimilarResult(
            path=result.path,
            title=result.title,
            type=result.type,
            tags=result.tags,
            score=result.score,
            snippet=result.snippet,
            similarity=round(similarity, 4),
            kind=similar_kind(similarity),
        )
    for candidate in _document_candidates(root, query, type_filter, tag_filters, system_filters):
        current = by_path.get(candidate.path)
        if current is None or candidate.similarity > current.similarity:
            by_path[candidate.path] = candidate
    return sorted(
        by_path.values(),
        key=lambda result: (-result.similarity, result.path),
    )[:limit]


def render_similar(results: Sequence[SimilarResult]) -> str:
    lines: list[str] = []
    for result in results:
        lines.append(
            f"{result.kind}: {result.path} :: {result.title} "
            f"(similarity={result.similarity:.4f})"
        )
        lines.append(result.snippet)
    return "\n".join(lines) + ("\n" if lines else "")
