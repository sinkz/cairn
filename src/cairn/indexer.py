from __future__ import annotations

import hashlib
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from cairn.config import is_excluded, load_config
from cairn.frontmatter import FrontmatterError, parse_document
from cairn.passages import split_passages
from cairn.ranking import fts_query, fts_query_variants, query_tokens, rrf_merge
from cairn.validate import RESERVED_NAMES
from cairn.vocabulary import expanded_fts_and_query, expanded_query_groups


class CairnIndexError(RuntimeError):
    pass


@dataclass(frozen=True)
class SearchResult:
    path: str
    title: str
    type: str
    tags: list[str]
    score: float
    snippet: str


@dataclass(frozen=True)
class PassageSearchResult:
    path: str
    title: str
    type: str
    tags: list[str]
    heading: str
    start_line: int
    end_line: int
    score: float
    snippet: str
    text: str


@dataclass(frozen=True)
class IndexStats:
    updated: int = 0
    removed: int = 0
    skipped: int = 0


@dataclass(frozen=True)
class QueryDiagnostics:
    strict_query: str
    zero_hit_terms: list[str]
    relaxed_query: str
    relaxation_applied: bool
    reason: str = ""


@dataclass(frozen=True)
class _SignalGroup:
    tokens: list[str]
    query: str
    df: int
    idf: float


@dataclass(frozen=True)
class _SignalState:
    eligible_groups: list[_SignalGroup]
    zero_hit_terms: list[str]
    dropped_groups: int
    total_signal_mass: float


_INDEX_ERROR = "search index is missing or invalid; run `apollokairn index --rebuild`"
_HIGHLIGHT_START = "__CAIRN_HIGHLIGHT_START__"
_HIGHLIGHT_END = "__CAIRN_HIGHLIGHT_END__"
_BM25_WEIGHTS = (0.1, 1.5, 8.0, 4.0, 6.0, 6.0, 5.0, 5.0, 0.2, 3.0)
_PASSAGE_BM25_WEIGHTS = (0.1, 1.5, 8.0, 6.0, 5.0, 4.0, 0.1, 0.1, 1.0, 3.0)
_RRF_K = 60
_MAX_RELAX_GROUPS = 8
_MAX_RELAX_CANDIDATES = 20
_MIN_DOCS_FOR_DF_LOW_SIGNAL = 30
_MIN_DF_FOR_LOW_SIGNAL = 10
_LOW_SIGNAL_DF_RATIO = 0.80
_MIN_RELAX_MATCHED_GROUPS = 2
_MIN_RELAX_COVERAGE = 0.60
_MIN_RELAX_SIGNAL_MASS = 0.81
_MIN_RELAX_SIGNAL_MASS_WITH_DROPS = 0.65
_SINGLE_SURVIVOR_MAX_DROPPED = 1
_RELAXATION_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "com",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "of",
    "on",
    "or",
    "os",
    "ou",
    "para",
    "por",
    "que",
    "sem",
    "the",
    "to",
    "um",
    "uma",
    "with",
}


def _db_path(root: Path) -> Path:
    return root / ".cairn" / "index.db"


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


def _as_text(value: object) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return "" if value is None else str(value)


def _content(*parts: str) -> str:
    return "\n".join(part for part in parts if part)


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


def _best_snippet(content_snippet: str, body_snippet: str) -> str:
    if _HIGHLIGHT_START in content_snippet and _HIGHLIGHT_END in content_snippet:
        snippet = content_snippet
    elif _HIGHLIGHT_START in body_snippet and _HIGHLIGHT_END in body_snippet:
        snippet = body_snippet
    else:
        snippet = content_snippet or body_snippet
    return snippet.replace(_HIGHLIGHT_START, "[").replace(_HIGHLIGHT_END, "]")


def _reset_schema(con: sqlite3.Connection) -> None:
    con.execute("DROP TABLE IF EXISTS docs")
    con.execute("DROP TABLE IF EXISTS passages")
    con.execute("DROP TABLE IF EXISTS index_meta")
    con.execute(
        "CREATE VIRTUAL TABLE docs USING fts5("
        "path, type, title, description, tags, aliases, systems, signals, body, content, "
        "tokenize = 'unicode61 remove_diacritics 2'"
        ")"
    )
    con.execute(
        "CREATE VIRTUAL TABLE passages USING fts5("
        "path UNINDEXED, type, title, tags, systems, heading, "
        "start_line UNINDEXED, end_line UNINDEXED, text, content, "
        "tokenize = 'unicode61 remove_diacritics 2'"
        ")"
    )
    con.execute(
        "CREATE TABLE index_meta(path TEXT PRIMARY KEY, mtime_ns INTEGER NOT NULL, size INTEGER NOT NULL, sha256 TEXT NOT NULL)"
    )


def _has_current_schema(con: sqlite3.Connection) -> bool:
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name IN ('docs', 'passages', 'index_meta')"
    ).fetchall()
    return {row[0] for row in rows} == {"docs", "passages", "index_meta"}


def _file_signature(path: Path) -> tuple[int, int, str]:
    stat = path.stat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return stat.st_mtime_ns, stat.st_size, digest


def _delete_doc(con: sqlite3.Connection, rel: str) -> None:
    con.execute("DELETE FROM docs WHERE path = ?", (rel,))
    con.execute("DELETE FROM passages WHERE path = ?", (rel,))
    con.execute("DELETE FROM index_meta WHERE path = ?", (rel,))


def _upsert_doc(
    con: sqlite3.Connection,
    root: Path,
    path: Path,
    mtime_ns: int,
    size: int,
    sha256: str,
) -> bool:
    rel = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8")
    try:
        parsed = parse_document(text)
    except FrontmatterError:
        _delete_doc(con, rel)
        return False
    fm = parsed.frontmatter
    typ = _as_text(fm.get("type"))
    title = _as_text(fm.get("title"))
    description = _as_text(fm.get("description"))
    tags = _as_text(fm.get("tags"))
    aliases = _as_text(fm.get("aliases"))
    systems = _as_text(fm.get("systems"))
    signals = _as_text(fm.get("signals"))
    con.execute("DELETE FROM docs WHERE path = ?", (rel,))
    con.execute("DELETE FROM passages WHERE path = ?", (rel,))
    con.execute(
        "INSERT INTO docs(path, type, title, description, tags, aliases, systems, signals, body, content) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            rel,
            typ,
            title,
            description,
            tags,
            aliases,
            systems,
            signals,
            parsed.body,
            _content(typ, title, description, tags, aliases, systems, signals),
        ),
    )
    for passage in split_passages(rel, text):
        con.execute(
            "INSERT INTO passages(path, type, title, tags, systems, heading, start_line, end_line, text, content) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                rel,
                typ,
                title,
                tags,
                systems,
                passage.heading,
                passage.start_line,
                passage.end_line,
                passage.text,
                _content(typ, title, tags, aliases, systems, signals, passage.heading),
            ),
        )
    con.execute(
        "INSERT OR REPLACE INTO index_meta(path, mtime_ns, size, sha256) VALUES (?, ?, ?, ?)",
        (rel, mtime_ns, size, sha256),
    )
    return True


def sync_index(root: Path, rebuild: bool = False) -> IndexStats:
    root = Path(root)
    db = _db_path(root)
    db.parent.mkdir(parents=True, exist_ok=True)
    try:
        con = sqlite3.connect(db)
    except sqlite3.Error as exc:
        raise CairnIndexError(_INDEX_ERROR) from exc
    try:
        try:
            if rebuild or not _has_current_schema(con):
                _reset_schema(con)

            updated = 0
            removed = 0
            skipped = 0
            paths = _concept_files(root)
            current_rel = {path.relative_to(root).as_posix() for path in paths}
            indexed = {
                row[0]: (row[1], row[2], row[3])
                for row in con.execute("SELECT path, mtime_ns, size, sha256 FROM index_meta").fetchall()
            }
            indexed_rel = set(indexed)

            for rel in sorted(indexed_rel - current_rel):
                _delete_doc(con, rel)
                removed += 1

            for path in paths:
                rel = path.relative_to(root).as_posix()
                row = indexed.get(rel)
                mtime_ns, size, sha256 = _file_signature(path)
                if row == (mtime_ns, size, sha256):
                    skipped += 1
                    continue
                if _upsert_doc(con, root, path, mtime_ns, size, sha256):
                    updated += 1
            con.commit()
            return IndexStats(updated=updated, removed=removed, skipped=skipped)
        except sqlite3.Error as exc:
            raise CairnIndexError(_INDEX_ERROR) from exc
    finally:
        try:
            con.close()
        except sqlite3.Error:
            pass


def rebuild_index(root: Path) -> None:
    sync_index(root, rebuild=True)


def repair_stale_index(root: Path) -> IndexStats | None:
    root = Path(root)
    db = _db_path(root)
    if not db.exists():
        return None
    if not db.is_file():
        raise CairnIndexError(_INDEX_ERROR)
    try:
        con = sqlite3.connect(db)
    except sqlite3.Error:
        raise CairnIndexError(_INDEX_ERROR)
    try:
        try:
            if not _has_current_schema(con):
                raise CairnIndexError(_INDEX_ERROR)
        except sqlite3.Error as exc:
            raise CairnIndexError(_INDEX_ERROR) from exc
    finally:
        con.close()
    return sync_index(root)


def _search_doc_rows(con: sqlite3.Connection, fts_query: str, candidate_limit: int) -> list[sqlite3.Row]:
    return con.execute(
        "SELECT path, type, title, tags, systems, "
        "bm25(docs, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) AS score, "
        "snippet(docs, 9, ?, ?, '...', 12), "
        "snippet(docs, 8, ?, ?, '...', 12) "
        "FROM docs WHERE docs MATCH ? ORDER BY score LIMIT ?",
        (
            *_BM25_WEIGHTS,
            _HIGHLIGHT_START,
            _HIGHLIGHT_END,
            _HIGHLIGHT_START,
            _HIGHLIGHT_END,
            fts_query,
            candidate_limit,
        ),
    ).fetchall()


def _append_diagnostics(target: list[QueryDiagnostics] | None, diagnostics: QueryDiagnostics) -> None:
    if target is not None:
        target.append(diagnostics)


def _dedupe_query_tokens(query: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for token in query_tokens(query):
        key = token.casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(token)
    return out


def _fts_query_from_tokens(tokens: Sequence[str]) -> str:
    return " ".join(f'"{token}"' for token in tokens)


def _query_term_groups(root: Path, query: str) -> list[list[str]]:
    groups = expanded_query_groups(root, query)
    if groups:
        return [group for group in groups if not _is_stopword_group(group)]
    return [[token] for token in _dedupe_query_tokens(query)]


def _is_stopword_group(group: Sequence[str]) -> bool:
    return all(token.casefold() in _RELAXATION_STOPWORDS for token in group)


def _fts_query_from_group(group: Sequence[str]) -> str:
    if len(group) == 1:
        return _fts_query_from_tokens(group)
    return "(" + " OR ".join(f'"{token}"' for token in group) + ")"


def _fts_query_from_groups(groups: Sequence[Sequence[str]]) -> str:
    return " AND ".join(_fts_query_from_group(group) for group in groups)


def _validate_fts_table(table: str) -> None:
    if table not in {"docs", "passages"}:
        raise ValueError("table must be 'docs' or 'passages'")


def _has_fts_match(con: sqlite3.Connection, table: str, query_text: str) -> bool:
    _validate_fts_table(table)
    if not query_text:
        return False
    return con.execute(
        f"SELECT 1 FROM {table} WHERE {table} MATCH ? LIMIT 1",
        (query_text,),
    ).fetchone() is not None


def _fts_row_count(con: sqlite3.Connection, table: str) -> int:
    _validate_fts_table(table)
    return int(con.execute(f"SELECT count(*) FROM {table}").fetchone()[0])


def _fts_match_count(con: sqlite3.Connection, table: str, query_text: str) -> int:
    _validate_fts_table(table)
    if not query_text:
        return 0
    return int(
        con.execute(
            f"SELECT count(*) FROM {table} WHERE {table} MATCH ?",
            (query_text,),
        ).fetchone()[0]
    )


def _is_low_signal_df(df: int, row_count: int) -> bool:
    return (
        row_count >= _MIN_DOCS_FOR_DF_LOW_SIGNAL
        and df >= _MIN_DF_FOR_LOW_SIGNAL
        and (df / row_count) >= _LOW_SIGNAL_DF_RATIO
    )


def _idf(row_count: int, df: int) -> float:
    return math.log((row_count + 1) / (df + 1)) + 1.0


def _signal_state(con: sqlite3.Connection, root: Path, table: str, query: str) -> _SignalState:
    row_count = _fts_row_count(con, table)
    eligible_groups: list[_SignalGroup] = []
    zero_hit_terms: list[str] = []
    dropped_groups = 0
    for group in _query_term_groups(root, query):
        if _is_stopword_group(group):
            dropped_groups += 1
            continue
        group_query = _fts_query_from_group(group)
        df = _fts_match_count(con, table, group_query)
        if df <= 0:
            zero_hit_terms.append(group[0])
            dropped_groups += 1
            continue
        if _is_low_signal_df(df, row_count):
            dropped_groups += 1
            continue
        eligible_groups.append(_SignalGroup(list(group), group_query, df, _idf(row_count, df)))
    total_signal_mass = sum(group.idf for group in eligible_groups)
    return _SignalState(eligible_groups, zero_hit_terms, dropped_groups, total_signal_mass)


def _candidate_rowids(
    con: sqlite3.Connection,
    table: str,
    query_text: str,
    candidate_limit: int,
) -> list[int]:
    _validate_fts_table(table)
    weights = _BM25_WEIGHTS if table == "docs" else _PASSAGE_BM25_WEIGHTS
    return [
        int(row[0])
        for row in con.execute(
            f"SELECT rowid, bm25({table}, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) AS score "
            f"FROM {table} WHERE {table} MATCH ? ORDER BY score LIMIT ?",
            (
                *weights,
                query_text,
                candidate_limit,
            ),
        ).fetchall()
    ]


def _row_matches_query(con: sqlite3.Connection, table: str, rowid: int, query_text: str) -> bool:
    _validate_fts_table(table)
    return con.execute(
        f"SELECT 1 FROM {table} WHERE rowid = ? AND {table} MATCH ? LIMIT 1",
        (rowid, query_text),
    ).fetchone() is not None


def _cooccurrence_relaxed_query(
    con: sqlite3.Connection,
    table: str,
    signal: _SignalState,
) -> str:
    if len(signal.eligible_groups) > _MAX_RELAX_GROUPS:
        return ""
    if len(signal.eligible_groups) == 1:
        return signal.eligible_groups[0].query
    candidate_query = " OR ".join(group.query for group in signal.eligible_groups)
    best_groups: list[_SignalGroup] = []
    best_key: tuple[float, float, int, int] | None = None
    for rank, rowid in enumerate(_candidate_rowids(con, table, candidate_query, _MAX_RELAX_CANDIDATES)):
        matched = [
            group
            for group in signal.eligible_groups
            if _row_matches_query(con, table, rowid, group.query)
        ]
        if len(matched) < _MIN_RELAX_MATCHED_GROUPS:
            continue
        coverage = len(matched) / len(signal.eligible_groups)
        signal_mass = sum(group.idf for group in matched)
        signal_ratio = signal_mass / signal.total_signal_mass if signal.total_signal_mass else 0.0
        min_signal_mass = (
            _MIN_RELAX_SIGNAL_MASS_WITH_DROPS
            if signal.dropped_groups
            else _MIN_RELAX_SIGNAL_MASS
        )
        if coverage < _MIN_RELAX_COVERAGE or signal_ratio < min_signal_mass:
            continue
        key = (signal_ratio, coverage, len(matched), -rank)
        if best_key is None or key > best_key:
            best_key = key
            best_groups = matched
    if not best_groups:
        return ""
    return _fts_query_from_groups([group.tokens for group in best_groups])


def _zero_hit_relaxation(
    con: sqlite3.Connection,
    root: Path,
    table: str,
    query: str,
    strict_query: str,
    strict_has_rows: bool,
) -> QueryDiagnostics:
    signal = _signal_state(con, root, table, query)
    if not signal.eligible_groups:
        return QueryDiagnostics(strict_query, signal.zero_hit_terms, "", False, "no_signal")
    if strict_has_rows:
        return QueryDiagnostics(strict_query, [], "", False)
    relaxed_query = _cooccurrence_relaxed_query(con, table, signal)
    enough_signal = not (
        len(signal.eligible_groups) == 1
        and signal.dropped_groups > _SINGLE_SURVIVOR_MAX_DROPPED
    )
    relaxation_applied = bool(
        relaxed_query
        and enough_signal
        and _has_fts_match(con, table, relaxed_query)
    )
    reason = "" if relaxation_applied else "no_signal"
    return QueryDiagnostics(strict_query, signal.zero_hit_terms, relaxed_query, relaxation_applied, reason)


def query_diagnostics(root: Path, query: str, scope: str = "documents") -> QueryDiagnostics:
    root = Path(root)
    table = "passages" if scope == "passages" else "docs"
    if scope not in {"documents", "passages"}:
        raise ValueError("scope must be 'documents' or 'passages'")
    query_text = fts_query(query)
    if not query_text:
        return QueryDiagnostics("", [], "", False)
    repair_stale_index(root)
    db = _db_path(root)
    if not db.exists():
        raise CairnIndexError(_INDEX_ERROR)
    try:
        con = sqlite3.connect(db)
    except sqlite3.Error as exc:
        raise CairnIndexError(_INDEX_ERROR) from exc
    try:
        try:
            return _zero_hit_relaxation(
                con,
                root,
                table,
                query,
                query_text,
                strict_has_rows=_has_fts_match(con, table, query_text),
            )
        except sqlite3.Error as exc:
            raise CairnIndexError(_INDEX_ERROR) from exc
    finally:
        con.close()


def _search_doc_rows_with_fallback(
    con: sqlite3.Connection,
    root: Path,
    query: str,
    query_text: str,
    candidate_limit: int,
    diagnostics: list[QueryDiagnostics] | None = None,
) -> list[sqlite3.Row]:
    signal = _signal_state(con, root, "docs", query)
    if not signal.eligible_groups:
        _append_diagnostics(diagnostics, QueryDiagnostics(query_text, signal.zero_hit_terms, "", False, "no_signal"))
        return []
    expanded = expanded_fts_and_query(root, query)
    if expanded and expanded != query_text:
        rows = _search_doc_rows(con, expanded, max(candidate_limit, 100))
        if rows:
            _append_diagnostics(diagnostics, QueryDiagnostics(query_text, [], "", False))
            return rows
    rows = _search_doc_rows(con, query_text, candidate_limit)
    if rows:
        _append_diagnostics(diagnostics, QueryDiagnostics(query_text, [], "", False))
        return rows
    query_diag = _zero_hit_relaxation(con, root, "docs", query, query_text, strict_has_rows=False)
    if query_diag.relaxation_applied and query_diag.relaxed_query:
        rows = _search_doc_rows(con, query_diag.relaxed_query, max(candidate_limit, 100))
        if rows:
            _append_diagnostics(diagnostics, query_diag)
            return rows
    _append_diagnostics(diagnostics, query_diag)
    return rows


def _search_passage_rows(con: sqlite3.Connection, fts_query: str, candidate_limit: int) -> list[sqlite3.Row]:
    return con.execute(
        "SELECT path, type, title, tags, systems, heading, start_line, end_line, "
        "bm25(passages, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) AS score, "
        "snippet(passages, 8, ?, ?, '...', 12), "
        "snippet(passages, 9, ?, ?, '...', 12), "
        "text "
        "FROM passages WHERE passages MATCH ? ORDER BY score LIMIT ?",
        (
            *_PASSAGE_BM25_WEIGHTS,
            _HIGHLIGHT_START,
            _HIGHLIGHT_END,
            _HIGHLIGHT_START,
            _HIGHLIGHT_END,
            fts_query,
            candidate_limit,
        ),
    ).fetchall()


def _search_passage_rows_with_fallback(
    con: sqlite3.Connection,
    root: Path,
    query: str,
    query_text: str,
    candidate_limit: int,
    diagnostics: list[QueryDiagnostics] | None = None,
) -> list[sqlite3.Row]:
    signal = _signal_state(con, root, "passages", query)
    if not signal.eligible_groups:
        _append_diagnostics(diagnostics, QueryDiagnostics(query_text, signal.zero_hit_terms, "", False, "no_signal"))
        return []
    expanded = expanded_fts_and_query(root, query)
    if expanded and expanded != query_text:
        rows = _search_passage_rows(con, expanded, max(candidate_limit, 100))
        if rows:
            _append_diagnostics(diagnostics, QueryDiagnostics(query_text, [], "", False))
            return rows
    rows = _search_passage_rows(con, query_text, candidate_limit)
    if rows:
        _append_diagnostics(diagnostics, QueryDiagnostics(query_text, [], "", False))
        return rows
    query_diag = _zero_hit_relaxation(con, root, "passages", query, query_text, strict_has_rows=False)
    if query_diag.relaxation_applied and query_diag.relaxed_query:
        rows = _search_passage_rows(con, query_diag.relaxed_query, max(candidate_limit, 100))
        if rows:
            _append_diagnostics(diagnostics, query_diag)
            return rows
    _append_diagnostics(diagnostics, query_diag)
    return rows


def _fts_query_variants_with_glossary(root: Path, query: str) -> list[str]:
    variants = fts_query_variants(query)
    expanded = expanded_fts_and_query(root, query)
    if expanded and expanded not in variants:
        variants.insert(1, expanded)
    return variants


def _rrf_doc_rows(con: sqlite3.Connection, root: Path, query: str, candidate_limit: int) -> list[sqlite3.Row]:
    variants = _fts_query_variants_with_glossary(root, query)
    runs: list[list[str]] = []
    fused: dict[str, tuple[sqlite3.Row, int, float]] = {}
    for variant in variants:
        run: list[str] = []
        for rank, row in enumerate(_search_doc_rows(con, variant, candidate_limit), start=1):
            path = str(row[0])
            score = float(row[5])
            run.append(path)
            previous = fused.get(path)
            if previous is None or rank < previous[1] or score < previous[2]:
                fused[path] = (row, rank, score)
        runs.append(run)
    return [fused[path][0] for path in rrf_merge(runs, k=_RRF_K) if path in fused]


def _passage_key(row: sqlite3.Row) -> str:
    return f"{row[0]}:{row[6]}:{row[7]}"


def _rrf_passage_rows(con: sqlite3.Connection, root: Path, query: str, candidate_limit: int) -> list[sqlite3.Row]:
    variants = _fts_query_variants_with_glossary(root, query)
    runs: list[list[str]] = []
    fused: dict[str, tuple[sqlite3.Row, int, float]] = {}
    for variant in variants:
        run: list[str] = []
        for rank, row in enumerate(_search_passage_rows(con, variant, candidate_limit), start=1):
            key = _passage_key(row)
            score = float(row[8])
            run.append(key)
            previous = fused.get(key)
            if previous is None or rank < previous[1] or score < previous[2]:
                fused[key] = (row, rank, score)
        runs.append(run)
    return [fused[key][0] for key in rrf_merge(runs, k=_RRF_K) if key in fused]


def search(
    root: Path,
    query: str,
    limit: int = 3,
    type_filter: str | None = None,
    tag_filters: Sequence[str] = (),
    system_filters: Sequence[str] = (),
    ranker: str = "bm25",
    diagnostics: list[QueryDiagnostics] | None = None,
) -> list[SearchResult]:
    root = Path(root)
    if limit <= 0:
        raise ValueError("limit must be positive")
    if ranker not in {"bm25", "rrf"}:
        raise ValueError("ranker must be 'bm25' or 'rrf'")
    query_text = fts_query(query)
    if not query_text:
        return []
    repair_stale_index(root)
    db = _db_path(root)
    if not db.exists():
        raise CairnIndexError(_INDEX_ERROR)
    try:
        con = sqlite3.connect(db)
    except sqlite3.Error as exc:
        raise CairnIndexError(_INDEX_ERROR) from exc
    try:
        try:
            candidate_limit = (
                max(limit * 20, 100)
                if ranker == "rrf" or type_filter or tag_filters or system_filters
                else limit
            )
            rows = (
                _rrf_doc_rows(con, root, query, candidate_limit)
                if ranker == "rrf"
                else _search_doc_rows_with_fallback(con, root, query, query_text, candidate_limit, diagnostics)
            )
            if ranker == "rrf":
                _append_diagnostics(diagnostics, QueryDiagnostics(query_text, [], "", False))
        except sqlite3.Error as exc:
            raise CairnIndexError(_INDEX_ERROR) from exc
    finally:
        con.close()
    results: list[SearchResult] = []
    for row in rows:
        tags = [tag for tag in row[3].split() if tag]
        systems = [system for system in row[4].split() if system]
        if not _matches_filters(row[1], tags, systems, type_filter, tag_filters, system_filters):
            continue
        results.append(
            SearchResult(
                path=row[0],
                type=row[1],
                title=row[2],
                tags=tags,
                score=float(row[5]),
                snippet=_best_snippet(row[6], row[7]),
            )
        )
        if len(results) >= limit:
            break
    return results


def search_passages(
    root: Path,
    query: str,
    limit: int = 3,
    type_filter: str | None = None,
    tag_filters: Sequence[str] = (),
    system_filters: Sequence[str] = (),
    ranker: str = "bm25",
    diagnostics: list[QueryDiagnostics] | None = None,
) -> list[PassageSearchResult]:
    root = Path(root)
    if limit <= 0:
        raise ValueError("limit must be positive")
    if ranker not in {"bm25", "rrf"}:
        raise ValueError("ranker must be 'bm25' or 'rrf'")
    query_text = fts_query(query)
    if not query_text:
        return []
    repair_stale_index(root)
    db = _db_path(root)
    if not db.exists():
        raise CairnIndexError(_INDEX_ERROR)
    try:
        con = sqlite3.connect(db)
    except sqlite3.Error as exc:
        raise CairnIndexError(_INDEX_ERROR) from exc
    try:
        try:
            candidate_limit = (
                max(limit * 20, 100)
                if ranker == "rrf" or type_filter or tag_filters or system_filters
                else limit
            )
            rows = (
                _rrf_passage_rows(con, root, query, candidate_limit)
                if ranker == "rrf"
                else _search_passage_rows_with_fallback(con, root, query, query_text, candidate_limit, diagnostics)
            )
            if ranker == "rrf":
                _append_diagnostics(diagnostics, QueryDiagnostics(query_text, [], "", False))
        except sqlite3.Error as exc:
            raise CairnIndexError(_INDEX_ERROR) from exc
    finally:
        con.close()
    results: list[PassageSearchResult] = []
    for row in rows:
        tags = [tag for tag in row[3].split() if tag]
        systems = [system for system in row[4].split() if system]
        if not _matches_filters(row[1], tags, systems, type_filter, tag_filters, system_filters):
            continue
        results.append(
            PassageSearchResult(
                path=row[0],
                type=row[1],
                title=row[2],
                tags=tags,
                heading=row[5],
                start_line=int(row[6]),
                end_line=int(row[7]),
                score=float(row[8]),
                snippet=_best_snippet(row[9], row[10]),
                text=row[11],
            )
        )
        if len(results) >= limit:
            break
    return results


def show(root: Path, rel_path: str) -> str:
    root = Path(root)
    path = (root / rel_path).resolve()
    if root.resolve() not in path.parents and path != root.resolve():
        raise ValueError("path must stay inside vault")
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(rel_path)
    return path.read_text(encoding="utf-8")
