from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from cairn.config import validate_config
from cairn.indexer import _concept_files, _db_path, _file_signature, _has_current_schema
from cairn.validate import validate_vault


@dataclass(frozen=True)
class DoctorReport:
    ok: bool
    lines: list[str]


def _index_lines(root: Path) -> tuple[bool, list[str]]:
    db = _db_path(root)
    if not db.exists():
        return False, ["ERROR index missing; run `apollokairn index --rebuild`"]
    try:
        con = sqlite3.connect(db)
    except sqlite3.Error:
        return False, ["ERROR index invalid; run `apollokairn index --rebuild`"]
    try:
        try:
            if not _has_current_schema(con):
                return False, ["ERROR index invalid; run `apollokairn index --rebuild`"]
            rows = con.execute("SELECT path, mtime_ns, size, sha256 FROM index_meta").fetchall()
        except sqlite3.Error:
            return False, ["ERROR index invalid; run `apollokairn index --rebuild`"]
    finally:
        con.close()

    indexed = {row[0]: (row[1], row[2], row[3]) for row in rows}
    current_paths = _concept_files(root)
    current = {path.relative_to(root).as_posix(): path for path in current_paths}
    missing = len(set(current) - set(indexed))
    removed = len(set(indexed) - set(current))
    changed = 0
    for rel, path in current.items():
        if rel not in indexed:
            continue
        if _file_signature(path) != indexed[rel]:
            changed += 1
    if missing or removed or changed:
        return False, [
            f"STALE index: changed {changed}, missing {missing}, removed {removed}; run `apollokairn index`"
        ]
    return True, ["OK index fresh"]


def check_vault(root: Path) -> DoctorReport:
    root = Path(root)
    lines: list[str] = []
    ok = True

    config_errors = validate_config(root)
    if config_errors:
        ok = False
        for error in config_errors:
            lines.append(f"ERROR config: {error}")
    else:
        lines.append("OK config")

    report = validate_vault(root)
    if report.errors:
        ok = False
        for issue in report.errors:
            lines.append(f"ERROR {issue.path}: {issue.message}")
    else:
        lines.append("OK validation")

    index_ok, index_lines = _index_lines(root)
    ok = ok and index_ok
    lines.extend(index_lines)
    return DoctorReport(ok=ok, lines=lines)
