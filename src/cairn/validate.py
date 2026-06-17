from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from cairn.config import is_excluded, load_config
from cairn.frontmatter import FrontmatterError, parse_document
from cairn.schema import parse_schema
from cairn.secret_scan import scan_text


RESERVED_NAMES = {
    "index.md",
    "log.md",
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "CODEX.md",
    "OPENCODE.md",
    "SCHEMA.md",
}
REQUIRED_FIELDS = ("type", "title", "description", "tags", "timestamp")
REQUIRED_SCALAR_FIELDS = ("type", "title", "description", "timestamp")


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str


@dataclass
class ValidationReport:
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)


def _is_iso8601(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    candidate = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(candidate)
    except ValueError:
        return False
    return True


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


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


def validate_vault(root: Path) -> ValidationReport:
    root = Path(root)
    report = ValidationReport()
    schema_path = root / "SCHEMA.md"
    if not schema_path.exists():
        report.errors.append(ValidationIssue("SCHEMA.md", "missing schema file"))
        return report

    schema = parse_schema(schema_path.read_text(encoding="utf-8"))

    for path in _concept_files(root):
        rel = path.relative_to(root).as_posix()
        raw = path.read_text(encoding="utf-8")
        for finding in scan_text(raw):
            report.errors.append(
                ValidationIssue(
                    rel,
                    f"potential secret detected: {finding.kind} on line {finding.line}",
                )
            )
        try:
            doc = parse_document(raw)
        except FrontmatterError as exc:
            report.errors.append(ValidationIssue(rel, str(exc)))
            continue
        fm = doc.frontmatter
        for field_name in REQUIRED_FIELDS:
            if field_name not in fm or fm[field_name] in ("", []):
                report.errors.append(ValidationIssue(rel, f"missing required field: {field_name}"))
        for field_name in REQUIRED_SCALAR_FIELDS:
            if field_name in fm and fm[field_name] not in ("", []) and not _is_non_empty_string(fm[field_name]):
                report.errors.append(ValidationIssue(rel, f"{field_name} must be a non-empty string"))
        typ = fm.get("type")
        if isinstance(typ, str) and typ and typ not in schema.types:
            report.errors.append(ValidationIssue(rel, f"type '{typ}' is not declared in SCHEMA.md"))
        tags = fm.get("tags", [])
        if not isinstance(tags, list):
            report.errors.append(ValidationIssue(rel, "tags must be a list"))
        else:
            for tag in tags:
                if isinstance(tag, str) and tag not in schema.tags:
                    report.errors.append(ValidationIssue(rel, f"tag '{tag}' is not declared in SCHEMA.md"))
        timestamp = fm.get("timestamp")
        if _is_non_empty_string(timestamp) and not _is_iso8601(timestamp):
            report.errors.append(ValidationIssue(rel, "timestamp must be ISO 8601"))

    return report
