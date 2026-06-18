from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path

from cairn import __version__
from cairn.profiles import list_profiles
from cairn.vault import init_vault


def _add_vault_path(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--path", default=".", help="Vault path. Defaults to current directory.")


def _read_text_input(value: str | None, file_path: str | None, use_stdin: bool) -> str:
    if file_path:
        return Path(file_path).read_text(encoding="utf-8")
    if use_stdin:
        return sys.stdin.read()
    return value or ""


def _json_ready(value: object) -> object:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    return value


def _print_json(value: object) -> None:
    print(json.dumps(_json_ready(value), ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cairn")
    parser.add_argument("--version", action="version", version=f"cairn {__version__}")
    sub = parser.add_subparsers(dest="command")

    init = sub.add_parser("init", help="Initialize a Cairn vault.")
    init.add_argument("--path", default=".", help="Vault path. Defaults to current directory.")
    init.add_argument(
        "--profile",
        default="personal",
        choices=list_profiles(),
    )

    def add_note_parser(name: str, help_text: str) -> argparse.ArgumentParser:
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--title", required=True)
        cmd.add_argument("--description", required=True)
        cmd.add_argument("--type", default="Note", dest="note_type")
        cmd.add_argument("--tag", action="append", default=[])
        cmd.add_argument("--folder", default="knowledge")
        body = cmd.add_mutually_exclusive_group()
        body.add_argument("--body", help="Inline Markdown body. Best for short text.")
        body.add_argument("--body-file", help="Read the Markdown body from a UTF-8 file.")
        body.add_argument("--body-stdin", action="store_true", help="Read the Markdown body from stdin.")
        cmd.add_argument("--alias", action="append", default=[])
        cmd.add_argument("--system", action="append", default=[])
        cmd.add_argument("--signal", action="append", default=[])
        cmd.add_argument("--timestamp")
        cmd.add_argument("--dry-run", action="store_true", help="Preview the write without changing files.")
        cmd.add_argument("--json", action="store_true")
        _add_vault_path(cmd)
        return cmd

    add_note_parser("add", "Create a new Cairn note.")
    add_note_parser("capture", "Capture reusable knowledge as a new note.")

    update_cmd = sub.add_parser("update", help="Update an existing Cairn note.")
    update_cmd.add_argument("document")
    append = update_cmd.add_mutually_exclusive_group(required=True)
    append.add_argument("--append", help="Inline text to append if it is not already present.")
    append.add_argument("--append-file", help="Read text to append from a UTF-8 file.")
    append.add_argument("--append-stdin", action="store_true", help="Read text to append from stdin.")
    update_cmd.add_argument("--dry-run", action="store_true", help="Preview the write without changing files.")
    update_cmd.add_argument("--expect-sha256", help="Only update if the current file hash matches this value.")
    update_cmd.add_argument("--json", action="store_true")
    _add_vault_path(update_cmd)

    export_cmd = sub.add_parser("export", help="Export a vault to a zip archive.")
    export_cmd.add_argument("--output", required=True)
    _add_vault_path(export_cmd)

    import_cmd = sub.add_parser("import", help="Import a vault zip archive.")
    import_cmd.add_argument("archive")
    _add_vault_path(import_cmd)

    stats_cmd = sub.add_parser("stats", help="Show vault statistics.")
    stats_cmd.add_argument("--json", action="store_true")
    _add_vault_path(stats_cmd)

    search_cmd = sub.add_parser("search", help="Search the vault.")
    search_cmd.add_argument("query")
    search_cmd.add_argument("--limit", type=int, default=3)
    search_cmd.add_argument("--ranker", choices=["bm25", "rrf"], default="bm25")
    search_cmd.add_argument("--json", action="store_true")
    search_cmd.add_argument("--type", dest="type_filter", help="Filter results by document type.")
    search_cmd.add_argument("--tag", action="append", default=[], help="Filter results by tag. Can be repeated.")
    search_cmd.add_argument("--system", action="append", default=[], help="Filter results by system. Can be repeated.")
    _add_vault_path(search_cmd)

    retrieve_cmd = sub.add_parser("retrieve", help="Retrieve a budgeted context packet.")
    retrieve_cmd.add_argument("query")
    retrieve_cmd.add_argument("--limit", type=int, default=3)
    retrieve_cmd.add_argument("--budget", type=int, default=1000, help="Approximate token budget.")
    retrieve_cmd.add_argument("--mode", choices=["documents", "passages"], default="documents")
    retrieve_cmd.add_argument("--ranker", choices=["bm25", "rrf", "auto"], default="bm25")
    retrieve_cmd.add_argument("--type", dest="type_filter", help="Filter results by document type.")
    retrieve_cmd.add_argument("--tag", action="append", default=[], help="Filter results by tag. Can be repeated.")
    retrieve_cmd.add_argument("--system", action="append", default=[], help="Filter results by system. Can be repeated.")
    retrieve_cmd.add_argument("--json", action="store_true")
    _add_vault_path(retrieve_cmd)

    similar_cmd = sub.add_parser("similar", help="Find existing notes before creating a duplicate.")
    similar_cmd.add_argument("query")
    similar_cmd.add_argument("--limit", type=int, default=5)
    similar_cmd.add_argument("--type", dest="type_filter", help="Filter results by document type.")
    similar_cmd.add_argument("--tag", action="append", default=[], help="Filter results by tag. Can be repeated.")
    similar_cmd.add_argument("--system", action="append", default=[], help="Filter results by system. Can be repeated.")
    similar_cmd.add_argument("--json", action="store_true")
    _add_vault_path(similar_cmd)

    show_cmd = sub.add_parser("show", help="Show a selected concept.")
    show_cmd.add_argument("document")
    show_cmd.add_argument("--lines", help="Show a 1-based inclusive line range, e.g. 10:25.")
    show_cmd.add_argument("--section", help="Show one Markdown section by heading text.")
    show_cmd.add_argument("--snippet", help="Show lines around the first matching text.")
    show_cmd.add_argument("--context", type=int, default=2, help="Snippet context lines.")
    show_cmd.add_argument("--json", action="store_true")
    _add_vault_path(show_cmd)

    index_cmd = sub.add_parser("index", help="Build or rebuild the search index.")
    index_cmd.add_argument("--rebuild", action="store_true")
    index_cmd.add_argument("--json", action="store_true")
    _add_vault_path(index_cmd)
    validate_cmd = sub.add_parser("validate", help="Validate the vault.")
    validate_cmd.add_argument("--json", action="store_true")
    _add_vault_path(validate_cmd)
    doctor_cmd = sub.add_parser("doctor", help="Check vault and index health.")
    doctor_cmd.add_argument("--json", action="store_true")
    _add_vault_path(doctor_cmd)

    setup_agent_cmd = sub.add_parser("setup-agent", help="Create an agent-specific Cairn guide.")
    setup_agent_cmd.add_argument("agent", choices=["agents", "codex", "claude", "opencode"])
    _add_vault_path(setup_agent_cmd)

    refresh_guides_cmd = sub.add_parser("refresh-guides", help="Refresh configured agent guides.")
    _add_vault_path(refresh_guides_cmd)

    vocab_cmd = sub.add_parser("vocab", help="Manage the deterministic Cairn glossary.")
    vocab_sub = vocab_cmd.add_subparsers(dest="vocab_command")
    vocab_add = vocab_sub.add_parser("add-term", help="Add or update an approved glossary term.")
    vocab_add.add_argument("term")
    vocab_add.add_argument("--alias", action="append", default=[])
    _add_vault_path(vocab_add)
    vocab_alias = vocab_sub.add_parser("add-alias", help="Add an alias to an approved glossary term.")
    vocab_alias.add_argument("term")
    vocab_alias.add_argument("alias")
    _add_vault_path(vocab_alias)
    vocab_suggest = vocab_sub.add_parser("suggest", help="Suggest glossary aliases from a query and the local vault.")
    vocab_suggest.add_argument("query")
    vocab_suggest.add_argument("--limit", type=int, default=5)
    vocab_suggest.add_argument("--json", action="store_true")
    _add_vault_path(vocab_suggest)
    vocab_validate = vocab_sub.add_parser("validate", help="Validate glossary terms and aliases.")
    vocab_validate.add_argument("--json", action="store_true")
    _add_vault_path(vocab_validate)
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
    if args.command in {"add", "capture"}:
        from cairn.notes import create_note

        try:
            body = _read_text_input(args.body, args.body_file, args.body_stdin)
            result = create_note(
                Path(args.path),
                title=args.title,
                description=args.description,
                typ=args.note_type,
                tags=args.tag,
                folder=args.folder,
                body=body,
                aliases=args.alias,
                systems=args.system,
                signals=args.signal,
                timestamp=args.timestamp,
                dry_run=args.dry_run,
            )
        except (FileExistsError, OSError, ValueError) as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        if args.json:
            _print_json(result)
        else:
            print(("would create" if args.dry_run else "created") + f" {result.path}")
        return 0
    if args.command == "update":
        from cairn.notes import append_to_note

        try:
            append_text = _read_text_input(args.append, args.append_file, args.append_stdin)
            result = append_to_note(
                Path(args.path),
                args.document,
                append_text,
                dry_run=args.dry_run,
                expected_sha256=args.expect_sha256,
            )
        except (FileNotFoundError, OSError, ValueError) as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        if args.json:
            _print_json(result)
        elif result.dry_run and result.would_change:
            print(f"would update {result.path}")
        else:
            print(("updated" if result.changed else "unchanged") + f" {result.path}")
        return 0
    if args.command == "export":
        from cairn.archive import export_vault

        try:
            output = export_vault(Path(args.path), Path(args.output))
        except (OSError, ValueError) as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        print(f"exported {output}")
        return 0
    if args.command == "import":
        from cairn.archive import import_vault

        try:
            root = import_vault(Path(args.archive), Path(args.path))
        except (OSError, ValueError) as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        print(f"imported {root}")
        return 0
    if args.command == "stats":
        from cairn.stats import collect_stats, render_stats

        stats = collect_stats(Path(args.path))
        if args.json:
            _print_json(stats)
        else:
            print(render_stats(stats), end="")
        return 0
    if args.command == "validate":
        from cairn.validate import validate_vault

        report = validate_vault(Path(args.path))
        if args.json:
            _print_json(
                {
                    "ok": not report.errors,
                    "error_count": len(report.errors),
                    "warning_count": len(report.warnings),
                    "errors": report.errors,
                    "warnings": report.warnings,
                }
            )
            return 1 if report.errors else 0
        for issue in report.errors:
            print(f"ERROR {issue.path}: {issue.message}")
        for issue in report.warnings:
            print(f"WARN {issue.path}: {issue.message}")
        return 1 if report.errors else 0
    if args.command == "doctor":
        from cairn.doctor import check_vault

        report = check_vault(Path(args.path))
        if args.json:
            _print_json(report)
            return 0 if report.ok else 1
        for line in report.lines:
            print(line)
        return 0 if report.ok else 1
    if args.command == "setup-agent":
        from cairn.guides import setup_agent

        try:
            result = setup_agent(Path(args.path), args.agent)
        except ValueError as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        print(f"updated {result.path}")
        return 0
    if args.command == "refresh-guides":
        from cairn.guides import refresh_guides

        for result in refresh_guides(Path(args.path)):
            print(f"updated {result.path}")
        return 0
    if args.command == "vocab":
        from cairn.vocabulary import add_alias, add_term, suggest_terms, validate_terms

        if args.vocab_command == "add-term":
            try:
                term = add_term(Path(args.path), args.term, args.alias)
            except ValueError as exc:
                print(f"ERROR {exc}", file=sys.stderr)
                return 1
            print(f"updated glossary.md :: {term.title}")
            return 0
        if args.vocab_command == "add-alias":
            try:
                term = add_alias(Path(args.path), args.term, args.alias)
            except ValueError as exc:
                print(f"ERROR {exc}", file=sys.stderr)
                return 1
            print(f"updated glossary.md :: {term.title}")
            return 0
        if args.vocab_command == "suggest":
            if args.limit <= 0:
                parser.error("--limit must be positive")
            report = suggest_terms(Path(args.path), args.query, limit=args.limit)
            if args.json:
                _print_json(report)
            else:
                for item in report.suggestions:
                    print(f"{item.term} -> {item.alias} ({item.path}, score={item.score:.4f})")
                    for evidence in item.evidence:
                        print(f"  - {evidence}")
            return 0
        if args.vocab_command == "validate":
            report = validate_terms(Path(args.path))
            if args.json:
                _print_json(report)
            else:
                for issue in report.errors:
                    print(f"ERROR {issue.term}: {issue.message}")
                for issue in report.warnings:
                    print(f"WARN {issue.term}: {issue.message}")
                if report.ok:
                    print(f"glossary ok ({report.term_count} terms, {report.alias_count} aliases)")
            return 0 if report.ok else 1
        parser.error("vocab requires a subcommand")
    if args.command == "index":
        from cairn.indexer import CairnIndexError, sync_index

        root = Path(args.path)
        index_path = root / ".cairn" / "index.db"
        try:
            stats = sync_index(root, rebuild=args.rebuild)
            if args.json:
                _print_json(
                    {
                        "ok": True,
                        "index_path": str(index_path),
                        "rebuild": args.rebuild,
                        "updated": stats.updated,
                        "removed": stats.removed,
                        "skipped": stats.skipped,
                    }
                )
            elif args.rebuild:
                print(f"rebuilt {index_path}")
            else:
                print(
                    f"indexed {index_path} "
                    f"(updated {stats.updated}, removed {stats.removed}, skipped {stats.skipped})"
                )
        except CairnIndexError as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        return 0
    if args.command == "search":
        from cairn.indexer import CairnIndexError, search

        if args.limit <= 0:
            parser.error("--limit must be positive")
        try:
            results = search(
                Path(args.path),
                args.query,
                limit=args.limit,
                type_filter=args.type_filter,
                tag_filters=args.tag,
                system_filters=args.system,
                ranker=args.ranker,
            )
        except CairnIndexError as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        if args.json:
            _print_json(results)
        else:
            for result in results:
                print(f"{result.path} :: {result.title}")
                print(result.snippet)
        return 0
    if args.command == "retrieve":
        from cairn.indexer import CairnIndexError
        from cairn.retriever import retrieve_packet

        if args.limit <= 0:
            parser.error("--limit must be positive")
        if args.budget <= 0:
            parser.error("--budget must be positive")
        try:
            packet = retrieve_packet(
                Path(args.path),
                args.query,
                limit=args.limit,
                budget_tokens=args.budget,
                mode=args.mode,
                type_filter=args.type_filter,
                tag_filters=args.tag,
                system_filters=args.system,
                ranker=args.ranker,
            )
        except (CairnIndexError, FileNotFoundError, ValueError) as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        if args.json:
            _print_json(packet)
        else:
            print(packet.context, end="")
        return 0
    if args.command == "similar":
        from cairn.indexer import CairnIndexError
        from cairn.similar import find_similar, render_similar

        if args.limit <= 0:
            parser.error("--limit must be positive")
        try:
            results = find_similar(
                Path(args.path),
                args.query,
                limit=args.limit,
                type_filter=args.type_filter,
                tag_filters=args.tag,
                system_filters=args.system,
            )
        except CairnIndexError as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        if args.json:
            _print_json(results)
        else:
            print(render_similar(results), end="")
        return 0
    if args.command == "show":
        from cairn.indexer import show
        from cairn.partials import extract_lines, extract_section, extract_snippet

        try:
            partial_modes = [
                bool(args.lines),
                bool(args.section),
                bool(args.snippet),
            ]
            if sum(partial_modes) > 1:
                parser.error("use only one of --lines, --section, or --snippet")
            text = show(Path(args.path), args.document)
            if args.lines:
                text = extract_lines(text, args.lines)
                mode = "lines"
                selector = args.lines
            elif args.section:
                text = extract_section(text, args.section)
                mode = "section"
                selector = args.section
            elif args.snippet:
                text = extract_snippet(text, args.snippet, context=args.context)
                mode = "snippet"
                selector = args.snippet
            else:
                mode = "document"
                selector = None
            if args.json:
                from cairn.retriever import approx_tokens

                _print_json(
                    {
                        "path": args.document,
                        "mode": mode,
                        "selector": selector,
                        "tokens": approx_tokens(text),
                        "content": text,
                    }
                )
            else:
                print(text, end="")
        except (FileNotFoundError, ValueError) as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        return 0
    parser.error(f"command not implemented yet: {args.command}")
    return 2
