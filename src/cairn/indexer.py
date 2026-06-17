from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from cairn.config import is_excluded, load_config
from cairn.frontmatter import FrontmatterError, parse_document
from cairn.validate import RESERVED_NAMES


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
class IndexStats:
    updated: int = 0
    removed: int = 0
    skipped: int = 0


_INDEX_ERROR = "search index is missing or invalid; run `cairn index --rebuild`"
_FTS_FIELD_PREFIX = re.compile(
    r"\b(?:path|type|title|description|tags|extra|body|content):",
    re.IGNORECASE,
)
_FTS_TOKEN = re.compile(r"\w+", re.UNICODE)
_FTS_OPERATORS = {"AND", "OR", "NOT", "NEAR"}
_HIGHLIGHT_START = "__CAIRN_HIGHLIGHT_START__"
_HIGHLIGHT_END = "__CAIRN_HIGHLIGHT_END__"
_BM25_WEIGHTS = (0.1, 1.5, 8.0, 4.0, 6.0, 6.0, 5.0, 5.0, 0.2, 3.0)


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


def _fts_query(query: str) -> str:
    cleaned = _FTS_FIELD_PREFIX.sub(" ", query)
    tokens = [
        token for token in _FTS_TOKEN.findall(cleaned)
        if token.upper() not in _FTS_OPERATORS
    ]
    return " ".join(f'"{token}"' for token in tokens)


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
    con.execute("DROP TABLE IF EXISTS index_meta")
    con.execute(
        "CREATE VIRTUAL TABLE docs USING fts5(path, type, title, description, tags, aliases, systems, signals, body, content)"
    )
    con.execute(
        "CREATE TABLE index_meta(path TEXT PRIMARY KEY, mtime_ns INTEGER NOT NULL, size INTEGER NOT NULL, sha256 TEXT NOT NULL)"
    )


def _has_current_schema(con: sqlite3.Connection) -> bool:
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name IN ('docs', 'index_meta')"
    ).fetchall()
    return {row[0] for row in rows} == {"docs", "index_meta"}


def _file_signature(path: Path) -> tuple[int, int, str]:
    stat = path.stat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return stat.st_mtime_ns, stat.st_size, digest


def _delete_doc(con: sqlite3.Connection, rel: str) -> None:
    con.execute("DELETE FROM docs WHERE path = ?", (rel,))
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
    try:
        parsed = parse_document(path.read_text(encoding="utf-8"))
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
            indexed_rel = {
                row[0] for row in con.execute("SELECT path FROM index_meta").fetchall()
            }

            for rel in sorted(indexed_rel - current_rel):
                _delete_doc(con, rel)
                removed += 1

            for path in paths:
                rel = path.relative_to(root).as_posix()
                mtime_ns, size, sha256 = _file_signature(path)
                row = con.execute(
                    "SELECT mtime_ns, size, sha256 FROM index_meta WHERE path = ?",
                    (rel,),
                ).fetchone()
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


def search(
    root: Path,
    query: str,
    limit: int = 3,
    type_filter: str | None = None,
    tag_filters: Sequence[str] = (),
    system_filters: Sequence[str] = (),
) -> list[SearchResult]:
    root = Path(root)
    if limit <= 0:
        raise ValueError("limit must be positive")
    fts_query = _fts_query(query)
    if not fts_query:
        return []
    db = _db_path(root)
    if not db.exists():
        raise CairnIndexError(_INDEX_ERROR)
    try:
        con = sqlite3.connect(db)
    except sqlite3.Error as exc:
        raise CairnIndexError(_INDEX_ERROR) from exc
    try:
        try:
            candidate_limit = max(limit * 20, 100) if type_filter or tag_filters or system_filters else limit
            rows = con.execute(
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


def show(root: Path, rel_path: str) -> str:
    root = Path(root)
    path = (root / rel_path).resolve()
    if root.resolve() not in path.parents and path != root.resolve():
        raise ValueError("path must stay inside vault")
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(rel_path)
    return path.read_text(encoding="utf-8")
