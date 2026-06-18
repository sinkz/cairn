from __future__ import annotations

import re
from typing import Sequence


_FTS_FIELD_PREFIX = re.compile(
    r"\b(?:path|type|title|description|tags|extra|body|content):",
    re.IGNORECASE,
)
_FTS_TOKEN = re.compile(r"\w+", re.UNICODE)
_FTS_OPERATORS = {"AND", "OR", "NOT", "NEAR"}
_SAFE_PREFIX_MIN_LENGTH = 5
_INFLECTION_SUFFIXES = (
    "ations",
    "ation",
    "ions",
    "ing",
    "ion",
    "ed",
)


def query_tokens(query: str) -> tuple[str, ...]:
    cleaned = _FTS_FIELD_PREFIX.sub(" ", query)
    return tuple(
        token for token in _FTS_TOKEN.findall(cleaned)
        if token.upper() not in _FTS_OPERATORS
    )


def fts_query(query: str) -> str:
    return " ".join(f'"{token}"' for token in query_tokens(query))


def fts_or_query(query: str) -> str:
    return " OR ".join(f'"{token}"' for token in query_tokens(query))


def _safe_prefix_token(token: str) -> str | None:
    if len(token) < _SAFE_PREFIX_MIN_LENGTH or not token.isalpha():
        return None
    if token.isupper():
        return None

    stem = token.casefold()
    for suffix in _INFLECTION_SUFFIXES:
        if stem.endswith(suffix) and len(stem) - len(suffix) >= _SAFE_PREFIX_MIN_LENGTH:
            stem = stem[: -len(suffix)]
            break
    else:
        if stem.endswith("s") and not stem.endswith("es") and len(stem) - 1 >= _SAFE_PREFIX_MIN_LENGTH:
            stem = stem[:-1]
    if len(stem) < _SAFE_PREFIX_MIN_LENGTH:
        return None
    return f"{stem}*"


def fts_prefix_query(query: str) -> str:
    terms: list[str] = []
    seen: set[str] = set()
    for token in query_tokens(query):
        term = _safe_prefix_token(token)
        if term is None or term in seen:
            continue
        seen.add(term)
        terms.append(term)
    return " OR ".join(terms)


def fts_query_variants(query: str) -> list[str]:
    variants = [fts_query(query), fts_or_query(query), fts_prefix_query(query)]
    out: list[str] = []
    for variant in variants:
        if variant and variant not in out:
            out.append(variant)
    return out


def rrf_merge(runs: Sequence[Sequence[str]], k: int = 60) -> list[str]:
    if k <= 0:
        raise ValueError("k must be positive")

    scores: dict[str, float] = {}
    best_rank: dict[str, int] = {}
    first_seen: dict[str, int] = {}
    order = 0

    for run in runs:
        seen_in_run: set[str] = set()
        for rank, item_id in enumerate(run, start=1):
            if item_id in seen_in_run:
                continue
            seen_in_run.add(item_id)
            if item_id not in first_seen:
                first_seen[item_id] = order
                order += 1
            scores[item_id] = scores.get(item_id, 0.0) + (1 / (k + rank))
            best_rank[item_id] = min(best_rank.get(item_id, rank), rank)

    return sorted(
        scores,
        key=lambda item_id: (
            -scores[item_id],
            best_rank[item_id],
            first_seen[item_id],
            item_id,
        ),
    )
