# Cairn Core MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first testable Cairn core: CLI skeleton, profile-based vault initialization, frontmatter/schema parsing, validation, indexing, search, and show.

**Architecture:** Implement a zero-runtime-dependency Python package under `src/cairn`. Markdown files are source of truth; `.cairn/index.db` is rebuildable state. The CLI exposes a small command surface and delegates behavior to focused modules.

**Tech Stack:** Python 3.11+ standard library only at runtime (`argparse`, `pathlib`, `json`, `sqlite3`, `datetime`, `re`, `unittest`, `tempfile`, `subprocess`).

---

## Scope

This plan implements PRD phases 0 and 1:

- package skeleton;
- `cairn` CLI;
- built-in profiles;
- `cairn init`;
- frontmatter parser;
- `SCHEMA.md` parser;
- `cairn validate`;
- SQLite FTS index;
- `cairn search`;
- `cairn show`.

Out of scope for this plan:

- `cairn add`;
- `cairn update`;
- `cairn capture`;
- duplicate detection;
- `cairn doctor`;
- `cairn guide refresh`;
- plugins, slash commands, MCP, UI.

## File Structure

- Create: `pyproject.toml` - package metadata and console script.
- Create: `src/cairn/__init__.py` - package version.
- Create: `src/cairn/__main__.py` - `python -m cairn` entrypoint.
- Create: `src/cairn/cli.py` - argparse command tree.
- Create: `src/cairn/profiles.py` - built-in profile definitions.
- Create: `src/cairn/templates.py` - generated file templates.
- Create: `src/cairn/vault.py` - vault initialization and path discovery.
- Create: `src/cairn/frontmatter.py` - restricted YAML frontmatter parser.
- Create: `src/cairn/schema.py` - `SCHEMA.md` parser.
- Create: `src/cairn/validate.py` - vault validation.
- Create: `src/cairn/indexer.py` - SQLite FTS indexing and search.
- Create: `tests/test_cli.py` - CLI smoke tests.
- Create: `tests/test_profiles.py` - profile/template tests.
- Create: `tests/test_init.py` - vault initialization tests.
- Create: `tests/test_frontmatter.py` - frontmatter parser tests.
- Create: `tests/test_schema.py` - schema parser tests.
- Create: `tests/test_validate.py` - validation tests.
- Create: `tests/test_indexer.py` - indexing/search/show tests.

---

### Task 1: Package Skeleton And CLI Smoke Test

**Files:**
- Create: `pyproject.toml`
- Create: `src/cairn/__init__.py`
- Create: `src/cairn/__main__.py`
- Create: `src/cairn/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing CLI smoke test**

```python
# tests/test_cli.py
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cairn(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "cairn", *args],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class CliSmokeTests(unittest.TestCase):
    def test_help_prints_command_list(self) -> None:
        result = run_cairn("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: cairn", result.stdout)
        self.assertIn("init", result.stdout)
        self.assertIn("search", result.stdout)
        self.assertIn("validate", result.stdout)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python -m unittest tests.test_cli -v
```

Expected: FAIL because module `cairn` does not exist.

- [ ] **Step 3: Add package metadata and minimal CLI**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "cairn"
version = "0.1.0"
description = "Agent-ready second brain for people and teams."
requires-python = ">=3.11"
dependencies = []

[project.scripts]
cairn = "cairn.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

```python
# src/cairn/__init__.py
__version__ = "0.1.0"
```

```python
# src/cairn/__main__.py
from cairn.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
```

```python
# src/cairn/cli.py
from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cairn")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("init", help="Initialize a Cairn vault.")
    sub.add_parser("search", help="Search the vault.")
    sub.add_parser("show", help="Show a selected concept.")
    sub.add_parser("index", help="Build or rebuild the search index.")
    sub.add_parser("validate", help="Validate the vault.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    parser.error(f"command not implemented yet: {args.command}")
    return 2
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
python -m unittest tests.test_cli -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/cairn tests/test_cli.py
git commit -m "feat: add cairn cli skeleton"
```

---

### Task 2: Built-In Profiles And Templates

**Files:**
- Create: `src/cairn/profiles.py`
- Create: `src/cairn/templates.py`
- Create: `tests/test_profiles.py`

- [ ] **Step 1: Write failing profile tests**

```python
# tests/test_profiles.py
from __future__ import annotations

import unittest

from cairn.profiles import get_profile, list_profiles
from cairn.templates import render_agents_md, render_schema_md


class ProfileTests(unittest.TestCase):
    def test_profiles_include_core_domains(self) -> None:
        self.assertEqual(
            list_profiles(),
            ["custom", "engineering", "personal", "product", "support"],
        )

    def test_engineering_profile_has_runbook_type(self) -> None:
        profile = get_profile("engineering")

        self.assertIn("Runbook", profile.types)
        self.assertIn("bug", profile.tags)
        self.assertIn("processes", profile.folders)

    def test_schema_template_lists_types_and_tags(self) -> None:
        profile = get_profile("support")
        text = render_schema_md(profile)

        self.assertIn("# Cairn Schema", text)
        self.assertIn("## Types", text)
        self.assertIn("- Procedure", text)
        self.assertIn("## Tags", text)
        self.assertIn("- escalation", text)

    def test_agents_template_contains_top_three_rule(self) -> None:
        profile = get_profile("personal")
        text = render_agents_md(profile)

        self.assertIn("cairn search", text)
        self.assertIn("Open at most the top 3", text)
        self.assertIn("Never store secrets", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m unittest tests.test_profiles -v
```

Expected: FAIL because `profiles.py` and `templates.py` do not exist.

- [ ] **Step 3: Implement profiles and templates**

```python
# src/cairn/profiles.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    name: str
    description: str
    types: tuple[str, ...]
    tags: tuple[str, ...]
    folders: tuple[str, ...]


_PROFILES: dict[str, Profile] = {
    "custom": Profile(
        name="custom",
        description="Minimal profile for custom domains.",
        types=("Note", "Reference"),
        tags=("general",),
        folders=("knowledge", "references", "notes", "inbox"),
    ),
    "engineering": Profile(
        name="engineering",
        description="Bugs, runbooks, decisions, incidents, libraries.",
        types=("Runbook", "Decision", "Process", "Reference", "Library"),
        tags=("bug", "incident", "deploy", "architecture", "library", "process"),
        folders=("knowledge", "processes", "decisions", "references", "notes", "inbox"),
    ),
    "personal": Profile(
        name="personal",
        description="Personal notes, learning, workflows, references.",
        types=("Note", "Process", "Decision", "Reference"),
        tags=("personal", "learning", "workflow", "reference", "idea"),
        folders=("knowledge", "processes", "decisions", "references", "notes", "inbox"),
    ),
    "product": Profile(
        name="product",
        description="Product decisions, requirements, discovery, metrics.",
        types=("Decision", "Requirement", "Research", "Metric", "Reference"),
        tags=("discovery", "stakeholder", "metric", "release", "requirement"),
        folders=("knowledge", "processes", "decisions", "references", "notes", "inbox"),
    ),
    "support": Profile(
        name="support",
        description="Support triage, procedures, escalations, FAQs.",
        types=("Procedure", "Known Issue", "FAQ", "Escalation", "Reference"),
        tags=("triage", "customer", "escalation", "faq", "procedure"),
        folders=("knowledge", "processes", "decisions", "references", "notes", "inbox"),
    ),
}


def list_profiles() -> list[str]:
    return sorted(_PROFILES)


def get_profile(name: str) -> Profile:
    try:
        return _PROFILES[name]
    except KeyError as exc:
        known = ", ".join(list_profiles())
        raise ValueError(f"unknown profile '{name}'. Known profiles: {known}") from exc
```

```python
# src/cairn/templates.py
from __future__ import annotations

from cairn.profiles import Profile


def render_schema_md(profile: Profile) -> str:
    type_lines = "\n".join(f"- {item}" for item in profile.types)
    tag_lines = "\n".join(f"- {item}" for item in profile.tags)
    return (
        "# Cairn Schema\n\n"
        f"Profile: `{profile.name}`\n\n"
        f"{profile.description}\n\n"
        "## Types\n\n"
        f"{type_lines}\n\n"
        "## Tags\n\n"
        f"{tag_lines}\n"
    )


def render_agents_md(profile: Profile) -> str:
    return (
        "# Cairn Agent Guide\n\n"
        f"Active profile: `{profile.name}`\n\n"
        "Before answering questions that may rely on saved knowledge, run "
        "`cairn search \"<query>\" --json`.\n\n"
        "Open at most the top 3 relevant documents with `cairn show <path>`.\n\n"
        "When reusable knowledge is learned, prefer updating an existing concept "
        "before creating a new one.\n\n"
        "Never store secrets, credentials, tokens, private keys, or passwords.\n"
    )


def render_concept_template(default_type: str = "Note") -> str:
    return (
        "---\n"
        f"type: {default_type}\n"
        "title:\n"
        "description:\n"
        "tags: []\n"
        "timestamp:\n"
        "aliases: []\n"
        "systems: []\n"
        "signals: []\n"
        "---\n\n"
        "# Context\n\n"
        "# Details\n\n"
        "# Next Steps\n"
    )
```

- [ ] **Step 4: Run the tests**

Run:

```bash
python -m unittest tests.test_profiles -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cairn/profiles.py src/cairn/templates.py tests/test_profiles.py
git commit -m "feat: add cairn profiles and templates"
```

---

### Task 3: Vault Initialization

**Files:**
- Create: `src/cairn/vault.py`
- Modify: `src/cairn/cli.py`
- Create: `tests/test_init.py`

- [ ] **Step 1: Write failing init tests**

```python
# tests/test_init.py
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cairn.vault import init_vault


class InitVaultTests(unittest.TestCase):
    def test_init_creates_profile_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = init_vault(root, profile_name="engineering")

            self.assertTrue((root / "AGENTS.md").exists())
            self.assertTrue((root / "SCHEMA.md").exists())
            self.assertTrue((root / "index.md").exists())
            self.assertTrue((root / "log.md").exists())
            self.assertTrue((root / ".cairn" / "config.json").exists())
            self.assertTrue((root / "_templates" / "concept.md").exists())
            self.assertTrue((root / "processes").is_dir())
            self.assertIn("AGENTS.md", result.created)

    def test_init_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            agents_path = root / "AGENTS.md"
            agents_path.write_text("custom guide\n", encoding="utf-8")

            result = init_vault(root, profile_name="personal")

            self.assertEqual(agents_path.read_text(encoding="utf-8"), "custom guide\n")
            self.assertIn("AGENTS.md", result.skipped)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m unittest tests.test_init -v
```

Expected: FAIL because `cairn.vault` does not exist.

- [ ] **Step 3: Implement init_vault**

```python
# src/cairn/vault.py
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from cairn.profiles import get_profile
from cairn.templates import render_agents_md, render_concept_template, render_schema_md


@dataclass
class InitResult:
    root: Path
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def _write_if_missing(path: Path, text: str, result: InitResult) -> None:
    rel = path.relative_to(result.root).as_posix()
    if path.exists():
        result.skipped.append(rel)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    result.created.append(rel)


def init_vault(root: Path, profile_name: str = "personal") -> InitResult:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    profile = get_profile(profile_name)
    result = InitResult(root=root)

    config = {
        "profile": profile.name,
        "search_limit": 3,
        "exclude": ["inbox"],
        "generated_guides": ["AGENTS.md"],
    }

    _write_if_missing(root / "AGENTS.md", render_agents_md(profile), result)
    _write_if_missing(root / "SCHEMA.md", render_schema_md(profile), result)
    _write_if_missing(root / "index.md", "# Cairn Vault\n\n", result)
    _write_if_missing(root / "log.md", "# Cairn Update Log\n\n", result)
    _write_if_missing(root / ".gitignore", ".cairn/index.db\n", result)
    _write_if_missing(
        root / ".cairn" / "config.json",
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        result,
    )
    _write_if_missing(
        root / "_templates" / "concept.md",
        render_concept_template(profile.types[0]),
        result,
    )

    for folder in profile.folders:
        path = root / folder
        rel = path.relative_to(root).as_posix()
        if path.exists():
            result.skipped.append(rel)
        else:
            path.mkdir(parents=True)
            result.created.append(rel)

    return result
```

- [ ] **Step 4: Wire `cairn init` in the CLI**

```python
# src/cairn/cli.py
from __future__ import annotations

import argparse
from pathlib import Path

from cairn.vault import init_vault


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cairn")
    sub = parser.add_subparsers(dest="command")

    init = sub.add_parser("init", help="Initialize a Cairn vault.")
    init.add_argument("--path", default=".", help="Vault path. Defaults to current directory.")
    init.add_argument(
        "--profile",
        default="personal",
        choices=["custom", "engineering", "personal", "product", "support"],
    )

    sub.add_parser("search", help="Search the vault.")
    sub.add_parser("show", help="Show a selected concept.")
    sub.add_parser("index", help="Build or rebuild the search index.")
    sub.add_parser("validate", help="Validate the vault.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "init":
        result = init_vault(Path(args.path), profile_name=args.profile)
        for item in result.created:
            print(f"created {item}")
        for item in result.skipped:
            print(f"skipped {item}")
        return 0
    parser.error(f"command not implemented yet: {args.command}")
    return 2
```

- [ ] **Step 5: Run tests**

Run:

```bash
python -m unittest tests.test_cli tests.test_init -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/cairn/cli.py src/cairn/vault.py tests/test_init.py
git commit -m "feat: initialize cairn vaults"
```

---

### Task 4: Frontmatter Parser

**Files:**
- Create: `src/cairn/frontmatter.py`
- Create: `tests/test_frontmatter.py`

- [ ] **Step 1: Write failing parser tests**

```python
# tests/test_frontmatter.py
from __future__ import annotations

import unittest

from cairn.frontmatter import FrontmatterError, parse_document


class FrontmatterTests(unittest.TestCase):
    def test_parse_simple_frontmatter(self) -> None:
        doc = parse_document(
            "---\n"
            "type: Note\n"
            "title: Demo\n"
            "tags: [personal, workflow]\n"
            "aliases:\n"
            "  - setup\n"
            "  - bootstrap\n"
            "---\n\n"
            "# Body\n"
        )

        self.assertEqual(doc.frontmatter["type"], "Note")
        self.assertEqual(doc.frontmatter["tags"], ["personal", "workflow"])
        self.assertEqual(doc.frontmatter["aliases"], ["setup", "bootstrap"])
        self.assertEqual(doc.body, "# Body\n")

    def test_missing_frontmatter_raises(self) -> None:
        with self.assertRaises(FrontmatterError):
            parse_document("# Body only\n")

    def test_unclosed_frontmatter_raises(self) -> None:
        with self.assertRaises(FrontmatterError):
            parse_document("---\ntype: Note\n")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python -m unittest tests.test_frontmatter -v
```

Expected: FAIL because `frontmatter.py` does not exist.

- [ ] **Step 3: Implement restricted parser**

```python
# src/cairn/frontmatter.py
from __future__ import annotations

from dataclasses import dataclass


class FrontmatterError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedDocument:
    frontmatter: dict[str, object]
    body: str


def _parse_scalar(value: str) -> object:
    value = value.strip()
    if value == "":
        return ""
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [part.strip().strip('"').strip("'") for part in inner.split(",")]
    return value.strip('"').strip("'")


def _parse_frontmatter(lines: list[str]) -> dict[str, object]:
    data: dict[str, object] = {}
    current_list_key: str | None = None
    for raw in lines:
        if not raw.strip():
            continue
        if raw.startswith("  - ") and current_list_key:
            data.setdefault(current_list_key, [])
            value = raw[4:].strip().strip('"').strip("'")
            cast = data[current_list_key]
            if isinstance(cast, list):
                cast.append(value)
            continue
        if ":" not in raw:
            raise FrontmatterError(f"invalid frontmatter line: {raw}")
        key, value = raw.split(":", 1)
        key = key.strip()
        if not key:
            raise FrontmatterError("empty frontmatter key")
        parsed = _parse_scalar(value)
        data[key] = parsed
        current_list_key = key if value.strip() == "" else None
        if current_list_key:
            data[key] = []
    return data


def parse_document(text: str) -> ParsedDocument:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("missing YAML frontmatter block")
    end_index: int | None = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break
    if end_index is None:
        raise FrontmatterError("unterminated YAML frontmatter block")
    fm_lines = [line.rstrip("\n") for line in lines[1:end_index]]
    body = "".join(lines[end_index + 1 :])
    if body.startswith("\n"):
        body = body[1:]
    return ParsedDocument(frontmatter=_parse_frontmatter(fm_lines), body=body)
```

- [ ] **Step 4: Run tests**

Run:

```bash
python -m unittest tests.test_frontmatter -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cairn/frontmatter.py tests/test_frontmatter.py
git commit -m "feat: parse cairn frontmatter"
```

---

### Task 5: Schema Parser

**Files:**
- Create: `src/cairn/schema.py`
- Create: `tests/test_schema.py`

- [ ] **Step 1: Write failing schema tests**

```python
# tests/test_schema.py
from __future__ import annotations

import unittest

from cairn.schema import parse_schema


class SchemaTests(unittest.TestCase):
    def test_parse_types_and_tags(self) -> None:
        schema = parse_schema(
            "# Cairn Schema\n\n"
            "Profile: `engineering`\n\n"
            "## Types\n\n"
            "- Runbook\n"
            "- Decision\n\n"
            "## Tags\n\n"
            "- bug\n"
            "- deploy\n"
        )

        self.assertEqual(schema.profile, "engineering")
        self.assertEqual(schema.types, {"Runbook", "Decision"})
        self.assertEqual(schema.tags, {"bug", "deploy"})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python -m unittest tests.test_schema -v
```

Expected: FAIL because `schema.py` does not exist.

- [ ] **Step 3: Implement schema parser**

```python
# src/cairn/schema.py
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
```

- [ ] **Step 4: Run tests**

Run:

```bash
python -m unittest tests.test_schema -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cairn/schema.py tests/test_schema.py
git commit -m "feat: parse cairn schema"
```

---

### Task 6: Vault Validation

**Files:**
- Create: `src/cairn/validate.py`
- Modify: `src/cairn/cli.py`
- Create: `tests/test_validate.py`

- [ ] **Step 1: Write failing validation tests**

```python
# tests/test_validate.py
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cairn.validate import validate_vault
from cairn.vault import init_vault


class ValidateTests(unittest.TestCase):
    def test_initialized_vault_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            concept = root / "knowledge" / "demo.md"
            concept.write_text(
                "---\n"
                "type: Note\n"
                "title: Demo\n"
                "description: A valid note.\n"
                "tags: [personal]\n"
                "timestamp: 2026-06-17T10:00:00Z\n"
                "---\n\n"
                "# Context\n",
                encoding="utf-8",
            )

            report = validate_vault(root)

            self.assertEqual(report.errors, [])

    def test_invalid_type_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            concept = root / "knowledge" / "bad.md"
            concept.write_text(
                "---\n"
                "type: Unknown\n"
                "title: Bad\n"
                "description: Bad note.\n"
                "tags: [personal]\n"
                "timestamp: 2026-06-17T10:00:00Z\n"
                "---\n\n"
                "# Context\n",
                encoding="utf-8",
            )

            report = validate_vault(root)

            self.assertEqual(len(report.errors), 1)
            self.assertIn("type", report.errors[0].message)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python -m unittest tests.test_validate -v
```

Expected: FAIL because `validate.py` does not exist.

- [ ] **Step 3: Implement validation**

```python
# src/cairn/validate.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from cairn.frontmatter import FrontmatterError, parse_document
from cairn.schema import parse_schema


RESERVED_NAMES = {"index.md", "log.md", "AGENTS.md", "CLAUDE.md", "CODEX.md", "SCHEMA.md"}
REQUIRED_FIELDS = ("type", "title", "description", "tags", "timestamp")


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


def _concept_files(root: Path) -> list[Path]:
    ignored_parts = {".cairn", "_templates"}
    out: list[Path] = []
    for path in root.rglob("*.md"):
        if path.name in RESERVED_NAMES:
            continue
        if any(part in ignored_parts for part in path.relative_to(root).parts):
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
        try:
            doc = parse_document(path.read_text(encoding="utf-8"))
        except FrontmatterError as exc:
            report.errors.append(ValidationIssue(rel, str(exc)))
            continue
        fm = doc.frontmatter
        for field_name in REQUIRED_FIELDS:
            if field_name not in fm or fm[field_name] in ("", []):
                report.errors.append(ValidationIssue(rel, f"missing required field: {field_name}"))
        typ = fm.get("type")
        if isinstance(typ, str) and typ and typ not in schema.types:
            report.errors.append(ValidationIssue(rel, f"type '{typ}' is not declared in SCHEMA.md"))
        tags = fm.get("tags", [])
        if not isinstance(tags, list):
            report.errors.append(ValidationIssue(rel, "tags must be a list"))
        else:
            for tag in tags:
                if isinstance(tag, str) and schema.tags and tag not in schema.tags:
                    report.errors.append(ValidationIssue(rel, f"tag '{tag}' is not declared in SCHEMA.md"))
        if "timestamp" in fm and not _is_iso8601(fm.get("timestamp")):
            report.errors.append(ValidationIssue(rel, "timestamp must be ISO 8601"))

    return report
```

- [ ] **Step 4: Wire `cairn validate`**

Add this branch in `main()` before the final parser error:

```python
    if args.command == "validate":
        from cairn.validate import validate_vault

        report = validate_vault(Path("."))
        for issue in report.errors:
            print(f"ERROR {issue.path}: {issue.message}")
        for issue in report.warnings:
            print(f"WARN {issue.path}: {issue.message}")
        return 1 if report.errors else 0
```

- [ ] **Step 5: Run tests**

Run:

```bash
python -m unittest tests.test_validate -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/cairn/cli.py src/cairn/validate.py tests/test_validate.py
git commit -m "feat: validate cairn vaults"
```

---

### Task 7: Index, Search, And Show

**Files:**
- Create: `src/cairn/indexer.py`
- Modify: `src/cairn/cli.py`
- Create: `tests/test_indexer.py`

- [ ] **Step 1: Write failing index/search tests**

```python
# tests/test_indexer.py
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cairn.indexer import rebuild_index, search, show
from cairn.vault import init_vault


class IndexerTests(unittest.TestCase):
    def test_search_returns_matching_snippet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="engineering")
            concept = root / "knowledge" / "deploy-403.md"
            concept.write_text(
                "---\n"
                "type: Runbook\n"
                "title: Fix deploy 403\n"
                "description: Fix deploy when permission returns 403.\n"
                "tags: [deploy, bug]\n"
                "timestamp: 2026-06-17T10:00:00Z\n"
                "signals: [HTTP 403, permission denied]\n"
                "---\n\n"
                "# Context\n\n"
                "Deploy fails with HTTP 403 during release.\n",
                encoding="utf-8",
            )
            rebuild_index(root)

            results = search(root, "HTTP 403 deploy", limit=3)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].path, "knowledge/deploy-403.md")
            self.assertIn("403", results[0].snippet)

    def test_show_returns_full_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_vault(root, profile_name="personal")
            concept = root / "knowledge" / "note.md"
            concept.write_text(
                "---\n"
                "type: Note\n"
                "title: Note\n"
                "description: A note.\n"
                "tags: [personal]\n"
                "timestamp: 2026-06-17T10:00:00Z\n"
                "---\n\n"
                "# Context\n\n"
                "Full body.\n",
                encoding="utf-8",
            )

            text = show(root, "knowledge/note.md")

            self.assertIn("type: Note", text)
            self.assertIn("Full body.", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python -m unittest tests.test_indexer -v
```

Expected: FAIL because `indexer.py` does not exist.

- [ ] **Step 3: Implement indexer**

```python
# src/cairn/indexer.py
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from cairn.frontmatter import FrontmatterError, parse_document
from cairn.validate import RESERVED_NAMES


@dataclass(frozen=True)
class SearchResult:
    path: str
    title: str
    type: str
    tags: list[str]
    score: float
    snippet: str


def _db_path(root: Path) -> Path:
    return root / ".cairn" / "index.db"


def _concept_files(root: Path) -> list[Path]:
    ignored_parts = {".cairn", "_templates"}
    out: list[Path] = []
    for path in root.rglob("*.md"):
        if path.name in RESERVED_NAMES:
            continue
        if any(part in ignored_parts for part in path.relative_to(root).parts):
            continue
        out.append(path)
    return sorted(out)


def _as_text(value: object) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return "" if value is None else str(value)


def rebuild_index(root: Path) -> None:
    root = Path(root)
    db = _db_path(root)
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    try:
        con.execute("DROP TABLE IF EXISTS docs")
        con.execute(
            "CREATE VIRTUAL TABLE docs USING fts5(path, type, title, description, tags, extra, body)"
        )
        for path in _concept_files(root):
            rel = path.relative_to(root).as_posix()
            try:
                parsed = parse_document(path.read_text(encoding="utf-8"))
            except FrontmatterError:
                continue
            fm = parsed.frontmatter
            extra = " ".join(
                _as_text(fm.get(key)) for key in ("aliases", "systems", "signals")
            )
            con.execute(
                "INSERT INTO docs(path, type, title, description, tags, extra, body) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    rel,
                    _as_text(fm.get("type")),
                    _as_text(fm.get("title")),
                    _as_text(fm.get("description")),
                    _as_text(fm.get("tags")),
                    extra,
                    parsed.body,
                ),
            )
        con.commit()
    finally:
        con.close()


def search(root: Path, query: str, limit: int = 3) -> list[SearchResult]:
    root = Path(root)
    con = sqlite3.connect(_db_path(root))
    try:
        rows = con.execute(
            "SELECT path, type, title, tags, bm25(docs) AS score, snippet(docs, 6, '[', ']', '...', 12) "
            "FROM docs WHERE docs MATCH ? ORDER BY score LIMIT ?",
            (query, limit),
        ).fetchall()
    finally:
        con.close()
    return [
        SearchResult(
            path=row[0],
            type=row[1],
            title=row[2],
            tags=[tag for tag in row[3].split() if tag],
            score=float(row[4]),
            snippet=row[5],
        )
        for row in rows
    ]


def show(root: Path, rel_path: str) -> str:
    root = Path(root)
    path = (root / rel_path).resolve()
    if root.resolve() not in path.parents and path != root.resolve():
        raise ValueError("path must stay inside vault")
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(rel_path)
    return path.read_text(encoding="utf-8")
```

- [ ] **Step 4: Wire CLI commands**

Add command arguments in `build_parser()`:

```python
    search_cmd = sub.add_parser("search", help="Search the vault.")
    search_cmd.add_argument("query")
    search_cmd.add_argument("--limit", type=int, default=3)
    search_cmd.add_argument("--json", action="store_true")

    show_cmd = sub.add_parser("show", help="Show a selected concept.")
    show_cmd.add_argument("path")

    index_cmd = sub.add_parser("index", help="Build or rebuild the search index.")
    index_cmd.add_argument("--rebuild", action="store_true")
```

Add command branches in `main()`:

```python
    if args.command == "index":
        from cairn.indexer import rebuild_index

        rebuild_index(Path("."))
        print("rebuilt .cairn/index.db")
        return 0
    if args.command == "search":
        import json
        from cairn.indexer import search

        results = search(Path("."), args.query, limit=args.limit)
        if args.json:
            print(json.dumps([result.__dict__ for result in results], indent=2))
        else:
            for result in results:
                print(f"{result.path} :: {result.title}")
                print(result.snippet)
        return 0
    if args.command == "show":
        from cairn.indexer import show

        print(show(Path("."), args.path), end="")
        return 0
```

- [ ] **Step 5: Run tests**

Run:

```bash
python -m unittest tests.test_indexer -v
```

Expected: PASS.

- [ ] **Step 6: Run all tests**

Run:

```bash
python -m unittest discover -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/cairn/cli.py src/cairn/indexer.py tests/test_indexer.py
git commit -m "feat: add cairn indexing and search"
```

---

### Task 8: Documentation Checkpoint

**Files:**
- Modify: `README.md`
- Modify: `docs/prd.md`
- Modify: `docs/plans/2026-06-17-cairn-design.md`

- [ ] **Step 1: Confirm docs match implemented command surface**

Run:

```bash
rg -n "cairn (init|search|show|index|validate|add|update|capture|doctor|guide|profile)" README.md docs
```

Expected: docs may mention future commands, but README quick-start should only
claim implemented commands after the MVP work is done.

- [ ] **Step 2: Add a README quick-start once tests pass**

Add this section to `README.md`:

````markdown
## Quick Start

```bash
python -m cairn init --profile personal
python -m cairn validate
python -m cairn index --rebuild
python -m cairn search "your query" --limit 3
```

The core runtime uses only the Python standard library.
````

- [ ] **Step 3: Run final verification**

Run:

```bash
python -m unittest discover -v
python -m cairn --help
```

Expected: tests PASS and help prints command list.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/prd.md docs/plans/2026-06-17-cairn-design.md
git commit -m "docs: align cairn mvp documentation"
```

---

## Self-Review

### Spec Coverage

- PRD local-first core: covered by stdlib-only CLI plan.
- Tool-agnostic core: covered by CLI and `AGENTS.md` generation.
- Domain-agnostic profiles: covered by profiles module and tests.
- OKF-compatible files: covered by frontmatter/schema validation.
- Token-efficient retrieval: covered by search snippets plus separate `show`.
- Rebuildable index: covered by `rebuild_index`.
- Future adapters: intentionally out of scope for this core MVP plan.

### Placeholder Scan

No task contains placeholder instructions or deferred implementation language.
Future features are explicitly marked out of scope.

### Type Consistency

The plan consistently uses:

- `Profile`;
- `InitResult`;
- `ParsedDocument`;
- `CairnSchema`;
- `ValidationReport`;
- `ValidationIssue`;
- `SearchResult`;
- commands rooted at `cairn`.
