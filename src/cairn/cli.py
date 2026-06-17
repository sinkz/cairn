from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cairn.profiles import list_profiles
from cairn.vault import init_vault


def _add_vault_path(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--path", default=".", help="Vault path. Defaults to current directory.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cairn")
    sub = parser.add_subparsers(dest="command")

    init = sub.add_parser("init", help="Initialize a Cairn vault.")
    init.add_argument("--path", default=".", help="Vault path. Defaults to current directory.")
    init.add_argument(
        "--profile",
        default="personal",
        choices=list_profiles(),
    )

    search_cmd = sub.add_parser("search", help="Search the vault.")
    search_cmd.add_argument("query")
    search_cmd.add_argument("--limit", type=int, default=3)
    search_cmd.add_argument("--json", action="store_true")
    search_cmd.add_argument("--type", dest="type_filter", help="Filter results by document type.")
    search_cmd.add_argument("--tag", action="append", default=[], help="Filter results by tag. Can be repeated.")
    search_cmd.add_argument("--system", action="append", default=[], help="Filter results by system. Can be repeated.")
    _add_vault_path(search_cmd)

    retrieve_cmd = sub.add_parser("retrieve", help="Retrieve a budgeted context packet.")
    retrieve_cmd.add_argument("query")
    retrieve_cmd.add_argument("--limit", type=int, default=3)
    retrieve_cmd.add_argument("--budget", type=int, default=1000, help="Approximate token budget.")
    retrieve_cmd.add_argument("--type", dest="type_filter", help="Filter results by document type.")
    retrieve_cmd.add_argument("--tag", action="append", default=[], help="Filter results by tag. Can be repeated.")
    retrieve_cmd.add_argument("--system", action="append", default=[], help="Filter results by system. Can be repeated.")
    _add_vault_path(retrieve_cmd)

    similar_cmd = sub.add_parser("similar", help="Find existing notes before creating a duplicate.")
    similar_cmd.add_argument("query")
    similar_cmd.add_argument("--limit", type=int, default=5)
    similar_cmd.add_argument("--type", dest="type_filter", help="Filter results by document type.")
    similar_cmd.add_argument("--tag", action="append", default=[], help="Filter results by tag. Can be repeated.")
    similar_cmd.add_argument("--system", action="append", default=[], help="Filter results by system. Can be repeated.")
    _add_vault_path(similar_cmd)

    show_cmd = sub.add_parser("show", help="Show a selected concept.")
    show_cmd.add_argument("document")
    show_cmd.add_argument("--lines", help="Show a 1-based inclusive line range, e.g. 10:25.")
    show_cmd.add_argument("--section", help="Show one Markdown section by heading text.")
    show_cmd.add_argument("--snippet", help="Show lines around the first matching text.")
    show_cmd.add_argument("--context", type=int, default=2, help="Snippet context lines.")
    _add_vault_path(show_cmd)

    index_cmd = sub.add_parser("index", help="Build or rebuild the search index.")
    index_cmd.add_argument("--rebuild", action="store_true")
    _add_vault_path(index_cmd)
    validate_cmd = sub.add_parser("validate", help="Validate the vault.")
    _add_vault_path(validate_cmd)
    doctor_cmd = sub.add_parser("doctor", help="Check vault and index health.")
    _add_vault_path(doctor_cmd)
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
    if args.command == "validate":
        from cairn.validate import validate_vault

        report = validate_vault(Path(args.path))
        for issue in report.errors:
            print(f"ERROR {issue.path}: {issue.message}")
        for issue in report.warnings:
            print(f"WARN {issue.path}: {issue.message}")
        return 1 if report.errors else 0
    if args.command == "doctor":
        from cairn.doctor import check_vault

        report = check_vault(Path(args.path))
        for line in report.lines:
            print(line)
        return 0 if report.ok else 1
    if args.command == "index":
        from cairn.indexer import CairnIndexError, rebuild_index, sync_index

        root = Path(args.path)
        try:
            if args.rebuild:
                rebuild_index(root)
                print(f"rebuilt {root / '.cairn' / 'index.db'}")
            else:
                stats = sync_index(root)
                print(
                    f"indexed {root / '.cairn' / 'index.db'} "
                    f"(updated {stats.updated}, removed {stats.removed}, skipped {stats.skipped})"
                )
        except CairnIndexError as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        return 0
    if args.command == "search":
        import json

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
            )
        except CairnIndexError as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps([result.__dict__ for result in results], indent=2))
        else:
            for result in results:
                print(f"{result.path} :: {result.title}")
                print(result.snippet)
        return 0
    if args.command == "retrieve":
        from cairn.indexer import CairnIndexError
        from cairn.retriever import retrieve

        if args.limit <= 0:
            parser.error("--limit must be positive")
        if args.budget <= 0:
            parser.error("--budget must be positive")
        try:
            print(
                retrieve(
                    Path(args.path),
                    args.query,
                    limit=args.limit,
                    budget_tokens=args.budget,
                    type_filter=args.type_filter,
                    tag_filters=args.tag,
                    system_filters=args.system,
                ),
                end="",
            )
        except (CairnIndexError, FileNotFoundError, ValueError) as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
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
            elif args.section:
                text = extract_section(text, args.section)
            elif args.snippet:
                text = extract_snippet(text, args.snippet, context=args.context)
            print(text, end="")
        except (FileNotFoundError, ValueError) as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        return 0
    parser.error(f"command not implemented yet: {args.command}")
    return 2
