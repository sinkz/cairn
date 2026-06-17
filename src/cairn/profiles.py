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
