from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from time import perf_counter

from cairn import __version__
from cairn.profiles import list_profiles
from cairn.vault import init_vault


PUBLIC_PROJECT_NAME = "ApolloKairn"
PUBLIC_COMMAND = "apollokairn"
LEGACY_COMMAND = "cairn"


def _add_vault_path(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--path", help="Vault path. Overrides registered vault selection.")
    parser.add_argument("--vault", help="Registered vault name. Ignored when --path is provided.")


def _read_text_input(value: str | None, file_path: str | None, use_stdin: bool) -> str:
    if file_path:
        return Path(file_path).read_text(encoding="utf-8")
    if use_stdin:
        return sys.stdin.read()
    return value or ""


def _json_ready(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return _json_ready(asdict(value))
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    return value


def _print_json(value: object) -> None:
    print(json.dumps(_json_ready(value), ensure_ascii=False, indent=2))


def _resolve_vault_path(args: argparse.Namespace) -> Path:
    from cairn.registry import resolve_vault_path

    return resolve_vault_path(path=getattr(args, "path", None), vault_name=getattr(args, "vault", None))


def _registry_payload(record: object, active: bool = False) -> dict[str, object]:
    from cairn.registry import status_for

    status = status_for(record, active=active)
    return {
        "name": status.name,
        "path": status.path,
        "active": status.active,
        "exists": status.exists,
        "is_vault": status.is_vault,
        "message": status.message,
    }


def _record_usage(
    root: str | Path,
    command: str,
    started_at: float,
    data: dict[str, object] | None = None,
    status: str = "ok",
    error: str | None = None,
) -> None:
    try:
        from cairn.usage import record_usage_event

        record_usage_event(Path(root), command, started_at, data=data, status=status, error=error)
    except Exception:
        return


def build_parser(prog: str = PUBLIC_COMMAND) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog)
    parser.add_argument("--version", action="version", version=f"{PUBLIC_COMMAND} {__version__}")
    sub = parser.add_subparsers(dest="command")

    init = sub.add_parser("init", help="Initialize a Cairn vault.")
    init.add_argument("--path", default=".", help="Vault path. Defaults to current directory.")
    init.add_argument(
        "--profile",
        default="personal",
        choices=list_profiles(),
    )
    init.add_argument("--json", action="store_true")

    vault_cmd = sub.add_parser("vault", help="Manage registered ApolloKairn vaults.")
    vault_sub = vault_cmd.add_subparsers(dest="vault_command")
    vault_add = vault_sub.add_parser("add", help="Register a vault path.")
    vault_add.add_argument("path")
    vault_add.add_argument("--name", required=True)
    vault_add.add_argument("--set-active", action="store_true", help="Make this vault active after registering it.")
    vault_add.add_argument("--json", action="store_true")
    vault_list = vault_sub.add_parser("list", help="List registered vaults.")
    vault_list.add_argument("--json", action="store_true")
    vault_current = vault_sub.add_parser("current", help="Show the active vault.")
    vault_current.add_argument("--json", action="store_true")
    vault_use = vault_sub.add_parser("use", help="Mark a registered vault as active.")
    vault_use.add_argument("name")
    vault_use.add_argument("--json", action="store_true")
    vault_show = vault_sub.add_parser("show", help="Show one registered vault.")
    vault_show.add_argument("name")
    vault_show.add_argument("--json", action="store_true")
    vault_remove = vault_sub.add_parser("remove", help="Remove a registered vault.")
    vault_remove.add_argument("name")
    vault_remove.add_argument("--json", action="store_true")
    vault_doctor = vault_sub.add_parser("doctor", help="Check registered vault paths.")
    vault_doctor.add_argument("--json", action="store_true")

    agent_cmd = sub.add_parser("agent", help="Install or check optional agent skills.")
    agent_sub = agent_cmd.add_subparsers(dest="agent_command")
    agent_install = agent_sub.add_parser("install", help="Install the ApolloKairn skill for an agent.")
    agent_install.add_argument("agent", choices=["codex", "hermes"])
    agent_install.add_argument("--scope", choices=["user", "repo"], default="user")
    agent_install.add_argument("--mode", choices=["copy", "symlink"], default="copy")
    agent_install.add_argument("--path", help="Repository path for --scope repo.")
    agent_install.add_argument("--target-dir", help="Override the skills directory.")
    agent_install.add_argument("--force", action="store_true", help="Overwrite an existing managed skill.")
    agent_install.add_argument("--dry-run", action="store_true", help="Show what would be installed without writing.")
    agent_install.add_argument("--json", action="store_true")
    agent_doctor = agent_sub.add_parser("doctor", help="Check installed ApolloKairn agent skills.")
    agent_doctor.add_argument("agent", nargs="?", choices=["codex", "hermes"])
    agent_doctor.add_argument("--scope", choices=["user", "repo"], default="user")
    agent_doctor.add_argument("--path", help="Repository path for --scope repo.")
    agent_doctor.add_argument("--target-dir", help="Override the skills directory.")
    agent_doctor.add_argument("--json", action="store_true")

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
    export_cmd.add_argument("--json", action="store_true")
    _add_vault_path(export_cmd)

    import_cmd = sub.add_parser("import", help="Import a vault zip archive.")
    import_cmd.add_argument("archive")
    import_cmd.add_argument("--json", action="store_true")
    _add_vault_path(import_cmd)

    stats_cmd = sub.add_parser("stats", help="Show vault statistics.")
    stats_cmd.add_argument("--json", action="store_true")
    _add_vault_path(stats_cmd)

    search_cmd = sub.add_parser("search", help="Search the vault.")
    search_cmd.add_argument("query")
    search_cmd.add_argument("--limit", type=int, default=3)
    search_cmd.add_argument("--ranker", choices=["bm25", "rrf"], default="bm25")
    search_cmd.add_argument("--json", action="store_true")
    search_cmd.add_argument("--explain", action="store_true", help="Include deterministic ranking explanations.")
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
    retrieve_cmd.add_argument("--explain", action="store_true", help="Include deterministic ranking explanations.")
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
    from cairn.guides import GUIDE_FILES

    setup_agent_cmd.add_argument("agent", choices=sorted(GUIDE_FILES))
    setup_agent_cmd.add_argument("--json", action="store_true")
    _add_vault_path(setup_agent_cmd)

    refresh_guides_cmd = sub.add_parser("refresh-guides", help="Refresh configured agent guides.")
    refresh_guides_cmd.add_argument("--json", action="store_true")
    _add_vault_path(refresh_guides_cmd)

    vocab_cmd = sub.add_parser("vocab", help="Manage the deterministic Cairn glossary.")
    vocab_sub = vocab_cmd.add_subparsers(dest="vocab_command")
    vocab_add = vocab_sub.add_parser("add-term", help="Add or update an approved glossary term.")
    vocab_add.add_argument("term")
    vocab_add.add_argument("--alias", action="append", default=[])
    vocab_add.add_argument("--json", action="store_true")
    _add_vault_path(vocab_add)
    vocab_alias = vocab_sub.add_parser("add-alias", help="Add an alias to an approved glossary term.")
    vocab_alias.add_argument("term")
    vocab_alias.add_argument("alias")
    vocab_alias.add_argument("--json", action="store_true")
    _add_vault_path(vocab_alias)
    vocab_suggest = vocab_sub.add_parser("suggest", help="Suggest glossary aliases from a query and the local vault.")
    vocab_suggest.add_argument("query")
    vocab_suggest.add_argument("--limit", type=int, default=5)
    vocab_suggest.add_argument("--json", action="store_true")
    _add_vault_path(vocab_suggest)
    vocab_lookup = vocab_sub.add_parser("lookup", help="Show approved glossary entries matching a query.")
    vocab_lookup.add_argument("query")
    vocab_lookup.add_argument("--json", action="store_true")
    _add_vault_path(vocab_lookup)
    vocab_validate = vocab_sub.add_parser("validate", help="Validate glossary terms and aliases.")
    vocab_validate.add_argument("--json", action="store_true")
    _add_vault_path(vocab_validate)

    usage_cmd = sub.add_parser("usage", help="Manage opt-in local usage metrics.")
    usage_sub = usage_cmd.add_subparsers(dest="usage_command")
    usage_enable = usage_sub.add_parser("enable", help="Enable local usage metrics for this vault.")
    usage_enable.add_argument("--json", action="store_true")
    _add_vault_path(usage_enable)
    usage_disable = usage_sub.add_parser("disable", help="Disable local usage metrics for this vault.")
    usage_disable.add_argument("--json", action="store_true")
    _add_vault_path(usage_disable)
    usage_status_cmd = usage_sub.add_parser("status", help="Show usage metrics status.")
    usage_status_cmd.add_argument("--json", action="store_true")
    _add_vault_path(usage_status_cmd)
    usage_report = usage_sub.add_parser("report", help="Summarize local usage metrics.")
    usage_report.add_argument("--html", action="store_true", help="Write a static HTML report.")
    usage_report.add_argument("--output", help="Optional HTML output path. Defaults to .cairn/reports/usage.html.")
    usage_report.add_argument("--json", action="store_true")
    _add_vault_path(usage_report)
    return parser


def _legacy_invocation_name(invoked_as: str | None) -> str:
    if invoked_as:
        return Path(invoked_as).stem.casefold()
    return Path(sys.argv[0]).stem.casefold()


def _warn_if_legacy_invocation(invoked_as: str | None) -> None:
    if _legacy_invocation_name(invoked_as) == LEGACY_COMMAND:
        print(
            f"WARNING: `{LEGACY_COMMAND}` is deprecated; use `{PUBLIC_COMMAND}` instead.",
            file=sys.stderr,
        )


def main(argv: list[str] | None = None, invoked_as: str | None = None) -> int:
    _warn_if_legacy_invocation(invoked_as)
    parser = build_parser()
    args = parser.parse_args(argv)
    started_at = perf_counter()
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "init":
        result = init_vault(Path(args.path), profile_name=args.profile)
        if args.json:
            _print_json(result)
        else:
            for item in result.created:
                print(f"created {item}")
            for item in result.skipped:
                print(f"skipped {item}")
        return 0
    if args.command == "vault":
        from cairn.registry import (
            RegistryError,
            add_vault,
            current_vault,
            doctor_vaults,
            list_vaults,
            load_registry,
            remove_vault,
            show_vault,
            use_vault,
        )

        try:
            if args.vault_command == "add":
                record = add_vault(Path(args.path), name=args.name, set_active=args.set_active)
                if args.json:
                    _print_json(_registry_payload(record, active=args.set_active))
                else:
                    suffix = " (active)" if args.set_active else ""
                    print(f"registered {record.name} -> {record.path}{suffix}")
                return 0
            if args.vault_command == "list":
                registry = load_registry()
                statuses = [_registry_payload(record, active=(record.name == registry.active)) for record in list_vaults()]
                if args.json:
                    _print_json({"active": registry.active, "vaults": statuses})
                elif not statuses:
                    print("no vaults registered")
                else:
                    for status in statuses:
                        marker = "*" if status["active"] else " "
                        print(f"{marker} {status['name']} -> {status['path']} ({status['message']})")
                return 0
            if args.vault_command == "current":
                record = current_vault()
                if record is None:
                    print("ERROR no active vault", file=sys.stderr)
                    return 1
                if args.json:
                    _print_json(_registry_payload(record, active=True))
                else:
                    print(f"{record.name} -> {record.path}")
                return 0
            if args.vault_command == "use":
                record = use_vault(args.name)
                if args.json:
                    _print_json(_registry_payload(record, active=True))
                else:
                    print(f"active {record.name} -> {record.path}")
                return 0
            if args.vault_command == "show":
                registry = load_registry()
                record = show_vault(args.name)
                payload = _registry_payload(record, active=(record.name == registry.active))
                if args.json:
                    _print_json(payload)
                else:
                    marker = "active " if payload["active"] else ""
                    print(f"{marker}{record.name} -> {record.path} ({payload['message']})")
                return 0
            if args.vault_command == "remove":
                record = remove_vault(args.name)
                if args.json:
                    _print_json(record)
                else:
                    print(f"removed {record.name}")
                return 0
            if args.vault_command == "doctor":
                registry = load_registry()
                statuses = doctor_vaults()
                ok = all(status.is_vault for status in statuses)
                if args.json:
                    _print_json({"ok": ok, "active": registry.active, "vaults": statuses})
                elif not statuses:
                    print("no vaults registered")
                else:
                    for status in statuses:
                        marker = "*" if status.active else " "
                        print(f"{marker} {status.name} -> {status.path} ({status.message})")
                return 0 if ok else 1
        except RegistryError as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        parser.error("vault requires a subcommand")
    if args.command == "agent":
        from cairn.agentic import AgenticError, doctor_agent_skills, install_agent_skill

        try:
            if args.agent_command == "install":
                result = install_agent_skill(
                    args.agent,
                    scope=args.scope,
                    mode=args.mode,
                    target_dir=args.target_dir,
                    repo_path=args.path,
                    force=args.force,
                    dry_run=args.dry_run,
                )
                if args.json:
                    _print_json(result)
                else:
                    action = "would install" if result.would_change and not result.changed else "installed"
                    if not result.would_change:
                        action = "already installed"
                    print(f"{action} {result.skill} for {result.agent} at {result.path}")
                return 0
            if args.agent_command == "doctor":
                report = doctor_agent_skills(
                    args.agent,
                    scope=args.scope,
                    target_dir=args.target_dir,
                    repo_path=args.path,
                )
                if args.json:
                    _print_json(report)
                else:
                    for check in report.checks:
                        print(f"{check.agent}: {check.message} ({check.path})")
                return 0 if report.ok else 1
        except AgenticError as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        parser.error("agent requires a subcommand")
    from cairn.registry import RegistryError

    try:
        root = _resolve_vault_path(args)
    except RegistryError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1
    if args.command == "usage":
        from cairn.usage import (
            render_usage_summary,
            set_usage_enabled,
            summarize_usage,
            usage_status,
            write_usage_report,
        )

        if args.usage_command == "enable":
            status = set_usage_enabled(root, True)
            if args.json:
                _print_json(status)
            else:
                print(f"usage metrics enabled ({status.events_path})")
            return 0
        if args.usage_command == "disable":
            status = set_usage_enabled(root, False)
            if args.json:
                _print_json(status)
            else:
                print("usage metrics disabled")
            return 0
        if args.usage_command == "status":
            status = usage_status(root)
            if args.json:
                _print_json(status)
            else:
                print(f"enabled: {str(status.enabled).lower()}")
                print(f"events: {status.event_count}")
                print(f"events_path: {status.events_path}")
                print(f"report_path: {status.report_path}")
            return 0
        if args.usage_command == "report":
            summary = write_usage_report(root, output=args.output) if args.html else summarize_usage(root)
            if args.json:
                _print_json(summary)
            else:
                print(render_usage_summary(summary), end="")
            return 0
        parser.error("usage requires a subcommand")
    if args.command in {"add", "capture"}:
        from cairn.notes import NotePolicyError, create_note, note_policy_payload

        try:
            body = _read_text_input(args.body, args.body_file, args.body_stdin)
            result = create_note(
                root,
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
        except NotePolicyError as exc:
            _record_usage(
                root,
                args.command,
                started_at,
                data={"path": exc.path, "type": args.note_type, "tags": args.tag, "dry_run": args.dry_run},
                status="error",
                error=str(exc),
            )
            if args.json:
                _print_json(note_policy_payload(exc))
            else:
                for issue in exc.issues:
                    print(f"ERROR {issue.path}: {issue.message}", file=sys.stderr)
            return 1
        except (FileExistsError, OSError, ValueError) as exc:
            _record_usage(
                root,
                args.command,
                started_at,
                data={"type": args.note_type, "tags": args.tag, "dry_run": args.dry_run},
                status="error",
                error=str(exc),
            )
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        _record_usage(
            root,
            args.command,
            started_at,
            data={
                "path": result.path,
                "changed": result.changed,
                "would_change": result.would_change,
                "dry_run": result.dry_run,
                "reason": result.reason,
                "type": args.note_type,
                "tags": args.tag,
            },
        )
        if args.json:
            _print_json(result)
        else:
            print(("would create" if args.dry_run else "created") + f" {result.path}")
        return 0
    if args.command == "update":
        from cairn.notes import NotePolicyError, append_to_note, note_policy_payload

        try:
            append_text = _read_text_input(args.append, args.append_file, args.append_stdin)
            result = append_to_note(
                root,
                args.document,
                append_text,
                dry_run=args.dry_run,
                expected_sha256=args.expect_sha256,
            )
        except NotePolicyError as exc:
            _record_usage(
                root,
                args.command,
                started_at,
                data={"document": args.document, "dry_run": args.dry_run},
                status="error",
                error=str(exc),
            )
            if args.json:
                _print_json(note_policy_payload(exc))
            else:
                for issue in exc.issues:
                    print(f"ERROR {issue.path}: {issue.message}", file=sys.stderr)
            return 1
        except (FileNotFoundError, OSError, ValueError) as exc:
            _record_usage(
                root,
                args.command,
                started_at,
                data={"document": args.document, "dry_run": args.dry_run},
                status="error",
                error=str(exc),
            )
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        _record_usage(
            root,
            args.command,
            started_at,
            data={
                "path": result.path,
                "document": args.document,
                "changed": result.changed,
                "would_change": result.would_change,
                "dry_run": result.dry_run,
                "reason": result.reason,
            },
        )
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
            output = export_vault(root, Path(args.output))
        except (OSError, ValueError) as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        if args.json:
            _print_json({"output": output})
        else:
            print(f"exported {output}")
        return 0
    if args.command == "import":
        from cairn.archive import import_vault

        try:
            imported_root = import_vault(Path(args.archive), root)
        except (OSError, ValueError) as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        if args.json:
            _print_json({"root": imported_root})
        else:
            print(f"imported {imported_root}")
        return 0
    if args.command == "stats":
        from cairn.stats import collect_stats, render_stats

        stats = collect_stats(root)
        _record_usage(
            root,
            args.command,
            started_at,
            data={
                "documents": stats.documents,
                "chars": stats.chars,
                "estimated_tokens": stats.estimated_tokens,
            },
        )
        if args.json:
            _print_json(stats)
        else:
            print(render_stats(stats), end="")
        return 0
    if args.command == "validate":
        from cairn.validate import validate_vault

        report = validate_vault(root)
        _record_usage(
            root,
            args.command,
            started_at,
            data={
                "ok": not report.errors,
                "error_count": len(report.errors),
                "warning_count": len(report.warnings),
            },
            status="ok" if not report.errors else "error",
            error="vault validation failed" if report.errors else None,
        )
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

        report = check_vault(root)
        _record_usage(
            root,
            args.command,
            started_at,
            data={"ok": report.ok},
            status="ok" if report.ok else "error",
            error="vault doctor failed" if not report.ok else None,
        )
        if args.json:
            _print_json(report)
            return 0 if report.ok else 1
        for line in report.lines:
            print(line)
        return 0 if report.ok else 1
    if args.command == "setup-agent":
        from cairn.guides import setup_agent

        try:
            result = setup_agent(root, args.agent)
        except ValueError as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        if args.json:
            _print_json(result)
        else:
            print(f"updated {result.path}")
        return 0
    if args.command == "refresh-guides":
        from cairn.guides import refresh_guides

        try:
            results = refresh_guides(root)
        except ValueError as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        if args.json:
            _print_json(results)
        else:
            for result in results:
                print(f"updated {result.path}")
        return 0
    if args.command == "vocab":
        from cairn.vocabulary import add_alias, add_term, lookup_terms, suggest_terms, validate_terms

        if args.vocab_command == "add-term":
            try:
                term = add_term(root, args.term, args.alias)
            except ValueError as exc:
                print(f"ERROR {exc}", file=sys.stderr)
                return 1
            if args.json:
                _print_json(term)
            else:
                print(f"updated glossary.md :: {term.title}")
            return 0
        if args.vocab_command == "add-alias":
            try:
                term = add_alias(root, args.term, args.alias)
            except ValueError as exc:
                print(f"ERROR {exc}", file=sys.stderr)
                return 1
            if args.json:
                _print_json(term)
            else:
                print(f"updated glossary.md :: {term.title}")
            return 0
        if args.vocab_command == "suggest":
            if args.limit <= 0:
                parser.error("--limit must be positive")
            report = suggest_terms(root, args.query, limit=args.limit)
            _record_usage(
                root,
                "vocab.suggest",
                started_at,
                data={"query": args.query, "limit": args.limit, "suggestion_count": len(report.suggestions)},
            )
            if args.json:
                _print_json(report)
            else:
                for item in report.suggestions:
                    print(f"{item.term} -> {item.alias} ({item.path}, score={item.score:.4f})")
                    for evidence in item.evidence:
                        print(f"  - {evidence}")
            return 0
        if args.vocab_command == "lookup":
            report = lookup_terms(root, args.query)
            _record_usage(
                root,
                "vocab.lookup",
                started_at,
                data={"query": args.query, "match_count": len(report.matches)},
            )
            if args.json:
                _print_json(report)
            else:
                for item in report.matches:
                    matched = ", ".join(item.matched)
                    expansion = ", ".join(item.expansion)
                    print(f"{item.term} :: matched [{matched}] -> expands [{expansion}]")
            return 0
        if args.vocab_command == "validate":
            report = validate_terms(root)
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

        index_path = root / ".cairn" / "index.db"
        try:
            stats = sync_index(root, rebuild=args.rebuild)
            _record_usage(
                root,
                args.command,
                started_at,
                data={
                    "rebuild": args.rebuild,
                    "updated": stats.updated,
                    "removed": stats.removed,
                    "skipped": stats.skipped,
                },
            )
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
            _record_usage(root, args.command, started_at, data={"rebuild": args.rebuild}, status="error", error=str(exc))
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        return 0
    if args.command == "search":
        from cairn.indexer import CairnIndexError, search
        from cairn.explain import explain_search_results

        if args.limit <= 0:
            parser.error("--limit must be positive")
        try:
            query_diagnostics = [] if args.explain else None
            results = search(
                root,
                args.query,
                limit=args.limit,
                type_filter=args.type_filter,
                tag_filters=args.tag,
                system_filters=args.system,
                ranker=args.ranker,
                diagnostics=query_diagnostics,
            )
        except CairnIndexError as exc:
            _record_usage(
                root,
                args.command,
                started_at,
                data={"query": args.query, "ranker": args.ranker, "limit": args.limit},
                status="error",
                error=str(exc),
            )
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        _record_usage(
            root,
            args.command,
            started_at,
            data={
                "query": args.query,
                "ranker": args.ranker,
                "limit": args.limit,
                "type": args.type_filter,
                "tags": args.tag,
                "systems": args.system,
                "result_count": len(results),
                "result_paths": [result.path for result in results],
            },
        )
        if args.explain:
            explanations = explain_search_results(root, args.query, results, args.ranker)
            if args.json:
                _print_json(
                    {
                        "query": args.query,
                        "ranker": args.ranker,
                        "query_diagnostics": query_diagnostics[0] if query_diagnostics else None,
                        "results": [
                            {"result": result, "explanation": explanation}
                            for result, explanation in zip(results, explanations)
                        ],
                    }
                )
            else:
                for result, explanation in zip(results, explanations):
                    print(f"{result.path} :: {result.title}")
                    print(result.snippet)
                    print(f"score: {explanation.score} ({explanation.score_note})")
                    if explanation.matched_fields:
                        print("matched_fields: " + ", ".join(explanation.matched_fields))
            return 0
        if args.json:
            _print_json(results)
        else:
            for result in results:
                print(f"{result.path} :: {result.title}")
                print(result.snippet)
        return 0
    if args.command == "retrieve":
        from cairn.explain import explain_retrieval_sources
        from cairn.indexer import CairnIndexError
        from cairn.retriever import retrieve_packet

        if args.limit <= 0:
            parser.error("--limit must be positive")
        if args.budget <= 0:
            parser.error("--budget must be positive")
        try:
            query_diagnostics = [] if args.explain else None
            packet = retrieve_packet(
                root,
                args.query,
                limit=args.limit,
                budget_tokens=args.budget,
                mode=args.mode,
                type_filter=args.type_filter,
                tag_filters=args.tag,
                system_filters=args.system,
                ranker=args.ranker,
                diagnostics=query_diagnostics,
            )
        except (CairnIndexError, FileNotFoundError, ValueError) as exc:
            _record_usage(
                root,
                args.command,
                started_at,
                data={"query": args.query, "ranker": args.ranker, "mode": args.mode, "limit": args.limit, "budget_tokens": args.budget},
                status="error",
                error=str(exc),
            )
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        _record_usage(
            root,
            args.command,
            started_at,
            data={
                "query": args.query,
                "requested_ranker": args.ranker,
                "ranker": packet.ranker,
                "mode": packet.mode,
                "limit": args.limit,
                "budget_tokens": packet.budget_tokens,
                "used_tokens": packet.used_tokens,
                "source_count": packet.source_count,
                "source_paths": [source.path for source in packet.sources],
            },
        )
        if args.explain:
            explanations = explain_retrieval_sources(root, args.query, packet.sources, packet.ranker)
            if args.json:
                _print_json(
                    {
                        "packet": packet,
                        "query_diagnostics": query_diagnostics[0] if query_diagnostics else None,
                        "explanations": explanations,
                    }
                )
            else:
                print(packet.context, end="")
                if explanations:
                    print("\n# Ranking Explanations")
                    for explanation in explanations:
                        location = f" ({explanation.heading})" if explanation.heading else ""
                        print(f"{explanation.path}{location}: {explanation.score} ({explanation.score_note})")
                        if explanation.matched_fields:
                            print("matched_fields: " + ", ".join(explanation.matched_fields))
            return 0
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
                root,
                args.query,
                limit=args.limit,
                type_filter=args.type_filter,
                tag_filters=args.tag,
                system_filters=args.system,
            )
        except CairnIndexError as exc:
            _record_usage(
                root,
                args.command,
                started_at,
                data={"query": args.query, "limit": args.limit},
                status="error",
                error=str(exc),
            )
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        _record_usage(
            root,
            args.command,
            started_at,
            data={
                "query": args.query,
                "limit": args.limit,
                "result_count": len(results),
                "result_paths": [result.path for result in results],
            },
        )
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
            text = show(root, args.document)
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
                _record_usage(
                    root,
                    args.command,
                    started_at,
                    data={"document": args.document, "mode": mode, "selector": selector, "tokens": approx_tokens(text)},
                )
            else:
                print(text, end="")
                from cairn.retriever import approx_tokens

                _record_usage(
                    root,
                    args.command,
                    started_at,
                    data={"document": args.document, "mode": mode, "selector": selector, "tokens": approx_tokens(text)},
                )
        except (FileNotFoundError, ValueError) as exc:
            _record_usage(
                root,
                args.command,
                started_at,
                data={"document": args.document},
                status="error",
                error=str(exc),
            )
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        return 0
    parser.error(f"command not implemented yet: {args.command}")
    return 2
