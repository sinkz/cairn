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
        '`cairn search "<query>" --json`.\n\n'
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
