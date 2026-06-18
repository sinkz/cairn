from __future__ import annotations

from cairn.profiles import Profile


def render_schema_md(profile: Profile) -> str:
    type_lines = "\n".join(f"- {item}" for item in profile.types)
    tag_lines = "\n".join(f"- {item}" for item in profile.tags)
    return (
        "# ApolloKairn Schema\n\n"
        f"Profile: `{profile.name}`\n\n"
        f"{profile.description}\n\n"
        "## Types\n\n"
        f"{type_lines}\n\n"
        "## Tags\n\n"
        f"{tag_lines}\n"
    )


def render_agents_md(profile: Profile) -> str:
    return (
        "# ApolloKairn Agent Guide\n\n"
        f"Active profile: `{profile.name}`\n\n"
        "## Before Answering\n\n"
        "1. Resolve the vault with `apollokairn vault current --json`, `apollokairn vault list --json`, `--vault <name>`, or `--path <vault>`.\n"
        "2. Run `apollokairn doctor --vault <name>` or `apollokairn doctor --path <vault>` when vault health is unknown.\n"
        "3. Run `apollokairn search \"<query>\" --vault <name> --json` or `apollokairn search \"<query>\" --path <vault> --json` for saved knowledge.\n"
        "4. Open at most the top 3 relevant documents.\n"
        "5. Prefer `apollokairn retrieve \"<query>\" --vault <name> --mode passages --ranker auto --budget 800 --json` or partial `apollokairn show` before reading full files.\n\n"
        "## After Solving\n\n"
        "1. Run `apollokairn similar \"<new knowledge>\" --vault <name>` or `apollokairn similar \"<new knowledge>\" --path <vault>`.\n"
        "2. Prefer `apollokairn update <path> --append \"<note>\" --vault <name>` when a related note exists.\n"
        "3. Use `apollokairn add` or `apollokairn capture` only for reusable knowledge that is not already represented.\n"
        "4. Use only types and tags declared in `SCHEMA.md`; ApolloKairn rejects invalid writes before creating files.\n"
        "5. Use `--body-file` or `--body-stdin` for multi-line Markdown instead of shell-escaped `\\n` text.\n"
        "6. Run `apollokairn validate --path <vault>` and `apollokairn index --path <vault>` after every successful write.\n\n"
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
