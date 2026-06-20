from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from cairn.config import is_excluded, load_config
from cairn.frontmatter import FrontmatterError, parse_document
from cairn.ranking import query_tokens
from cairn.validate import RESERVED_NAMES


GLOSSARY_FILE = "glossary.md"
_HEADING = re.compile(r"^##\s+(.+?)\s*$")
_FIELD = re.compile(r"^([A-Za-z][A-Za-z_-]*):\s*(.*?)\s*$")


@dataclass(frozen=True)
class VocabularyTerm:
    title: str
    aliases: list[str] = field(default_factory=list)
    status: str = "approved"
    scope: str = ""


@dataclass(frozen=True)
class VocabularyIssue:
    term: str
    message: str


@dataclass(frozen=True)
class VocabularyReport:
    ok: bool
    term_count: int
    alias_count: int
    errors: list[VocabularyIssue]
    warnings: list[VocabularyIssue]


@dataclass(frozen=True)
class VocabularySuggestion:
    term: str
    alias: str
    path: str
    score: float
    evidence: list[str]


@dataclass(frozen=True)
class VocabularySuggestionReport:
    query: str
    suggestions: list[VocabularySuggestion]


@dataclass(frozen=True)
class VocabularyLookupMatch:
    term: str
    aliases: list[str]
    status: str
    scope: str
    matched: list[str]
    expansion: list[str]


@dataclass(frozen=True)
class VocabularyLookupReport:
    query: str
    matches: list[VocabularyLookupMatch]


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def glossary_path(root: Path) -> Path:
    return Path(root) / GLOSSARY_FILE


def load_terms(root: Path) -> list[VocabularyTerm]:
    path = glossary_path(root)
    if not path.exists():
        return []
    terms: list[VocabularyTerm] = []
    current_title: str | None = None
    fields: dict[str, str] = {}

    def flush() -> None:
        nonlocal current_title, fields
        if current_title is None:
            return
        terms.append(
            VocabularyTerm(
                title=current_title.strip(),
                aliases=_split_csv(fields.get("aliases", "")),
                status=fields.get("status", "approved").strip() or "approved",
                scope=fields.get("scope", "").strip(),
            )
        )
        current_title = None
        fields = {}

    for line in path.read_text(encoding="utf-8").splitlines():
        heading = _HEADING.match(line)
        if heading:
            flush()
            current_title = heading.group(1)
            fields = {}
            continue
        if current_title is None:
            continue
        field_match = _FIELD.match(line.strip())
        if field_match:
            fields[field_match.group(1).casefold()] = field_match.group(2).strip()
    flush()
    return terms


def _render_terms(terms: Sequence[VocabularyTerm]) -> str:
    lines = [
        "# Glossary",
        "",
        "Approved aliases in this file are used for deterministic ApolloKairn query expansion.",
        "",
    ]
    for term in sorted(terms, key=lambda item: _normalize(item.title)):
        lines.extend(
            [
                f"## {term.title}",
                "",
                f"aliases: {', '.join(term.aliases)}",
                f"status: {term.status or 'approved'}",
            ]
        )
        if term.scope:
            lines.append(f"scope: {term.scope}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_terms(root: Path, terms: Sequence[VocabularyTerm]) -> None:
    glossary_path(root).write_text(_render_terms(terms), encoding="utf-8")


def add_term(root: Path, title: str, aliases: Sequence[str]) -> VocabularyTerm:
    title = title.strip()
    if not title:
        raise ValueError("term title must not be empty")
    existing = load_terms(root)
    normalized_title = _normalize(title)
    merged: list[VocabularyTerm] = []
    updated: VocabularyTerm | None = None
    for term in existing:
        if _normalize(term.title) != normalized_title:
            merged.append(term)
            continue
        seen = {_normalize(alias) for alias in term.aliases}
        new_aliases = list(term.aliases)
        for alias in aliases:
            alias = alias.strip()
            if alias and _normalize(alias) not in seen:
                seen.add(_normalize(alias))
                new_aliases.append(alias)
        updated = VocabularyTerm(term.title, new_aliases, term.status, term.scope)
        merged.append(updated)
    if updated is None:
        updated = VocabularyTerm(title, [alias.strip() for alias in aliases if alias.strip()])
        merged.append(updated)
    write_terms(root, merged)
    return updated


def add_alias(root: Path, title: str, alias: str) -> VocabularyTerm:
    return add_term(root, title, [alias])


def validate_terms(root: Path) -> VocabularyReport:
    errors: list[VocabularyIssue] = []
    warnings: list[VocabularyIssue] = []
    terms = load_terms(root)
    seen_terms: set[str] = set()
    alias_owner: dict[str, str] = {}
    approved = [term for term in terms if term.status.casefold() == "approved"]
    for term in terms:
        normalized_title = _normalize(term.title)
        if normalized_title in seen_terms:
            errors.append(VocabularyIssue(term.title, "duplicate term"))
        seen_terms.add(normalized_title)
        if term.status.casefold() not in {"approved", "draft"}:
            warnings.append(VocabularyIssue(term.title, f"unknown status '{term.status}'"))
        for alias in term.aliases:
            normalized_alias = _normalize(alias)
            owner = alias_owner.get(normalized_alias)
            if owner and owner != term.title:
                errors.append(VocabularyIssue(term.title, f"alias '{alias}' also belongs to '{owner}'"))
            else:
                alias_owner[normalized_alias] = term.title
    return VocabularyReport(
        ok=not errors,
        term_count=len(approved),
        alias_count=sum(len(term.aliases) for term in approved),
        errors=errors,
        warnings=warnings,
    )


def expanded_query_tokens(root: Path, query: str) -> list[str]:
    tokens = list(query_tokens(query))
    if not tokens:
        return []
    groups = _approved_token_groups(root)

    out: list[str] = []
    seen: set[str] = set()
    changed = False
    for token in tokens:
        token_norm = _normalize(token)
        candidates = {token}
        for group in groups:
            if token_norm in {_normalize(item) for item in group}:
                candidates.update(group)
        if len(candidates) > 1:
            changed = True
        for candidate in sorted(candidates, key=lambda item: (item != token, item.casefold())):
            key = _normalize(candidate)
            if key in seen:
                continue
            seen.add(key)
            out.append(candidate)
    return out if changed else []


def expanded_query_groups(root: Path, query: str) -> list[list[str]]:
    tokens = list(query_tokens(query))
    if not tokens:
        return []
    groups = _approved_token_groups(root)
    out: list[list[str]] = []
    seen_groups: set[tuple[str, ...]] = set()
    changed = False
    for token in tokens:
        token_norm = _normalize(token)
        candidates = {token}
        for group in groups:
            if token_norm in {_normalize(item) for item in group}:
                candidates.update(group)
        if len(candidates) > 1:
            changed = True
        normalized_group = tuple(sorted({_normalize(candidate) for candidate in candidates}))
        if normalized_group in seen_groups:
            continue
        seen_groups.add(normalized_group)
        ordered: list[str] = []
        seen_candidates: set[str] = set()
        for candidate in sorted(candidates, key=lambda item: (item != token, item.casefold())):
            key = _normalize(candidate)
            if key in seen_candidates:
                continue
            seen_candidates.add(key)
            ordered.append(candidate)
        out.append(ordered)
    return out if changed else []


def expanded_fts_or_query(root: Path, query: str) -> str:
    return " OR ".join(f'"{token}"' for token in expanded_query_tokens(root, query))


def expanded_fts_and_query(root: Path, query: str) -> str:
    parts: list[str] = []
    for group in expanded_query_groups(root, query):
        if len(group) == 1:
            parts.append(f'"{group[0]}"')
        else:
            parts.append("(" + " OR ".join(f'"{token}"' for token in group) + ")")
    return " AND ".join(parts)


def lookup_terms(root: Path, query: str) -> VocabularyLookupReport:
    query_norms = {_normalize(token) for token in query_tokens(query)}
    matches: list[VocabularyLookupMatch] = []
    for term in load_terms(root):
        if term.status.casefold() != "approved":
            continue
        values = [term.title, *term.aliases]
        matched: list[str] = []
        for value in values:
            tokens = list(query_tokens(value))
            if tokens and all(_normalize(token) in query_norms for token in tokens):
                matched.append(value)
        if not matched:
            continue
        matches.append(
            VocabularyLookupMatch(
                term=term.title,
                aliases=list(term.aliases),
                status=term.status,
                scope=term.scope,
                matched=_dedupe_values(matched),
                expansion=_dedupe_values(values),
            )
        )
    matches.sort(key=lambda item: _normalize(item.term))
    return VocabularyLookupReport(query=query, matches=matches)


def _approved_token_groups(root: Path) -> list[set[str]]:
    groups: list[set[str]] = []
    for term in load_terms(root):
        if term.status.casefold() != "approved":
            continue
        group: set[str] = set(query_tokens(term.title))
        for alias in term.aliases:
            group.update(query_tokens(alias))
        if group:
            groups.append(group)
    return groups


def _dedupe_values(values: Sequence[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        key = _normalize(cleaned)
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


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


def _compact_alias_match(term: str, alias: str) -> bool:
    term_norm = _normalize(term)
    alias_norm = _normalize(alias)
    if len(term_norm) < 5 or len(alias_norm) > 8:
        return False
    if not any(char.isdigit() for char in alias_norm):
        return False
    return term_norm[0] == alias_norm[0] and term_norm[-1] == alias_norm[-1]


def suggest_terms(root: Path, query: str, limit: int = 5) -> VocabularySuggestionReport:
    query_items = list(query_tokens(query))
    query_norms = {_normalize(token): token for token in query_items}
    suggestions: list[VocabularySuggestion] = []
    for path in _concept_files(Path(root)):
        rel = path.relative_to(root).as_posix()
        try:
            raw = path.read_text(encoding="utf-8")
            parsed = parse_document(raw)
        except (OSError, FrontmatterError):
            continue
        title = str(parsed.frontmatter.get("title", ""))
        description = str(parsed.frontmatter.get("description", ""))
        aliases = parsed.frontmatter.get("aliases", [])
        alias_text = " ".join(str(item) for item in aliases) if isinstance(aliases, list) else str(aliases or "")
        haystack = "\n".join([title, description, alias_text, parsed.body])
        doc_tokens = list(query_tokens(haystack))
        doc_norms = {_normalize(token): token for token in doc_tokens}
        shared = sorted(set(query_norms) & set(doc_norms))
        if not shared:
            continue
        missing_query_terms = [
            original for norm, original in query_norms.items()
            if norm not in doc_norms and len(norm) >= 5
        ]
        compact_aliases = [
            original for norm, original in doc_norms.items()
            if norm not in query_norms and len(norm) <= 8 and any(char.isdigit() for char in norm)
        ]
        for term in missing_query_terms:
            for alias in compact_aliases:
                if not _compact_alias_match(term, alias):
                    continue
                evidence = [
                    f"candidate note: {rel}",
                    "shared terms: " + ", ".join(query_norms[item] for item in shared),
                    f"compact alias candidate: {alias}",
                ]
                suggestions.append(
                    VocabularySuggestion(
                        term=term,
                        alias=alias,
                        path=rel,
                        score=round(0.5 + min(len(shared), 4) * 0.1, 4),
                        evidence=evidence,
                    )
                )
    suggestions.sort(key=lambda item: (-item.score, item.path, item.term.casefold(), item.alias.casefold()))
    return VocabularySuggestionReport(query=query, suggestions=suggestions[:limit])
