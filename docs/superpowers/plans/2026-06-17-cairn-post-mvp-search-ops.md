# Cairn Post-MVP Search Ops Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve Cairn after the Core MVP with lower-token retrieval, better operational safety, and stronger local search behavior.

**Architecture:** Keep Cairn local-first and Python stdlib-only. Add small focused modules for config, index health, partial rendering, and duplicate suggestions while preserving the existing CLI and tests.

**Tech Stack:** Python 3.11+, argparse, sqlite3 FTS5, unittest, Markdown files with YAML-like frontmatter.

---

## File Structure

- Modify `src/cairn/cli.py`: expose new command flags and commands.
- Modify `src/cairn/indexer.py`: support config excludes, incremental indexing, metadata filters, and boosted ranking.
- Create `src/cairn/config.py`: read `.cairn/config.json` and decide ignored paths.
- Create `src/cairn/doctor.py`: report vault/index health.
- Create `src/cairn/partials.py`: extract lines, sections, and snippets from Markdown.
- Create `src/cairn/similar.py`: provide duplicate/similar-note suggestions.
- Modify `src/cairn/validate.py`: honor config excludes.
- Modify `README.md`: document post-MVP commands.
- Add/modify tests under `tests/`.

## Tasks

### Task 1: Config Excludes

- [ ] Write failing tests for `validate` and `index` honoring `.cairn/config.json` `exclude`.
- [ ] Implement `src/cairn/config.py`.
- [ ] Wire config excludes into `validate.py` and `indexer.py`.
- [ ] Run focused tests, then `python -m unittest discover -v`.

### Task 2: Incremental Index And Staleness

- [ ] Write failing tests for incremental update after edit and removal.
- [ ] Add index metadata table with file mtime, size, and sha256.
- [ ] Make `cairn index` incremental by default and keep `--rebuild`.
- [ ] Run focused tests, then `python -m unittest discover -v`.

### Task 3: Boosted Ranking

- [ ] Write failing test proving title/tag/system matches outrank body-only noise.
- [ ] Apply explicit FTS5 BM25 weights.
- [ ] Run focused tests, then `python -m unittest discover -v`.

### Task 4: Partial Show

- [ ] Write failing tests for `show --lines`, `show --section`, and `show --snippet`.
- [ ] Implement Markdown partial extraction.
- [ ] Wire options into `cairn show`.
- [ ] Run focused tests, then `python -m unittest discover -v`.

### Task 5: Similar/Dedupe

- [ ] Write failing CLI test for `cairn similar "query"`.
- [ ] Implement duplicate suggestion using existing search results.
- [ ] Run focused tests, then `python -m unittest discover -v`.

### Task 6: Doctor

- [ ] Write failing tests for missing/stale/fresh index health.
- [ ] Implement `cairn doctor --path`.
- [ ] Run focused tests, then `python -m unittest discover -v`.

### Task 7: Final Battery

- [ ] Rebuild `.sandbox/battery-vault`.
- [ ] Run validate/index/search/show/retrieve/similar/doctor.
- [ ] Compare token cost against the prior baseline.
- [ ] Clean generated Python caches.
