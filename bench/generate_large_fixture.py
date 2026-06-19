from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "bench" / "fixtures" / "vault-large"
TOPICS = ROOT / "bench" / "topics-large.jsonl"
QRELS = ROOT / "bench" / "qrels-large.tsv"
GOLDEN = ROOT / "bench" / "golden-large.json"
TASKS = ROOT / "bench" / "agent" / "tasks-large.jsonl"


DOMAINS = [
    ("deploy", "deployment", "release", "artifact", "rollback"),
    ("auth", "authentication", "session", "token", "identity"),
    ("cache", "cache", "worker", "failover", "reconnection"),
    ("database", "database", "pool", "checkout", "connection"),
    ("support", "support", "customer", "escalation", "severity"),
    ("access", "access", "approval", "audit", "breakglass"),
    ("mobile", "mobile", "build", "store", "release"),
    ("billing", "billing", "invoice", "payment", "ledger"),
    ("observability", "observability", "alert", "trace", "dashboard"),
    ("search", "search", "index", "retrieval", "ranking"),
]

SYMPTOMS = [
    ("403", "forbidden", "authorization denied"),
    ("expired", "stale", "invalid state"),
    ("timeout", "latency", "slow response"),
    ("missing", "not found", "absent record"),
    ("duplicate", "repeat", "repeated entry"),
    ("drift", "skew", "clock mismatch"),
    ("saturation", "pressure", "capacity limit"),
    ("mismatch", "inconsistent", "contract difference"),
]

TYPES = ["Runbook", "Decision", "Process", "Reference"]


@dataclass(frozen=True)
class Case:
    index: int
    category: str
    domain: tuple[str, str, str, str, str]
    symptom: tuple[str, str, str]

    @property
    def id(self) -> str:
        return f"q_large_{self.index:03d}"

    @property
    def stem(self) -> str:
        return f"{self.domain[0]}-{self.symptom[0]}-{self.index:03d}"

    @property
    def query(self) -> str:
        keyword, area, system, signal, action = self.domain
        code, symptom, phrase = self.symptom
        if self.category == "paraphrase":
            return f"{phrase} {area} {action} recovery playbook"
        if self.category == "pt_br":
            return f"{area} {symptom} resolver incidente cliente prioridade"
        if self.category == "role_workflow":
            return f"owner triage {area} {symptom} customer impact escalation"
        if self.category == "cross_doc":
            return f"{area} {system} {signal} {symptom} decision runbook"
        if self.category == "passage_budget":
            return f"{area} {signal} {symptom} diagnosis resolution checklist"
        if self.category == "noisy_query":
            return f"{area} {code} {signal} {symptom} asteroid irrelevant extra"
        if self.category == "filtered":
            return f"{area} {signal} {symptom} {action}"
        if self.category == "no_answer":
            return "unmapped constellation payroll zephyr"
        return f"{area} {code} {signal} {symptom} {action}"

    @property
    def topic(self) -> dict[str, object]:
        topic: dict[str, object] = {
            "id": self.id,
            "query": self.query,
            "category": self.category,
            "budget": 700,
        }
        if self.category == "passage_budget":
            topic["mode"] = "passages"
            topic["compare_mode"] = "documents"
            topic["budget"] = 300
        if self.category == "noisy_query":
            topic["ranker"] = "rrf"
            topic["compare_ranker"] = "bm25"
        if self.category == "filtered":
            topic["type"] = "Runbook"
            topic["system"] = self.domain[0]
        return topic


def _category(index: int) -> str:
    if index <= 5:
        return "no_answer"
    if index <= 17:
        return "exact_error"
    if index <= 27:
        return "paraphrase"
    if index <= 37:
        return "role_workflow"
    if index <= 47:
        return "cross_doc"
    if index <= 55:
        return "pt_br"
    if index <= 65:
        return "passage_budget"
    if index <= 74:
        return "noisy_query"
    return "filtered"


def _cases() -> list[Case]:
    cases: list[Case] = []
    for index in range(1, 81):
        domain = DOMAINS[(index - 1) // len(SYMPTOMS)]
        symptom = SYMPTOMS[(index - 1) % len(SYMPTOMS)]
        cases.append(Case(index=index, category=_category(index), domain=domain, symptom=symptom))
    return cases


def _slug(value: str) -> str:
    return "-".join(part for part in value.replace("_", "-").split() if part)


def _frontmatter(
    typ: str,
    title: str,
    description: str,
    tags: list[str],
    aliases: list[str],
    systems: list[str],
    signals: list[str],
) -> str:
    return (
        "---\n"
        f"type: {typ}\n"
        f"title: {title}\n"
        f"description: {description}\n"
        f"tags: [{', '.join(tags)}]\n"
        "timestamp: 2026-06-19T00:00:00Z\n"
        f"aliases: [{', '.join(aliases)}]\n"
        f"systems: [{', '.join(systems)}]\n"
        f"signals: [{', '.join(signals)}]\n"
        "---\n\n"
    )


def _write_note(path: Path, typ: str, title: str, description: str, tags: list[str], aliases: list[str], systems: list[str], signals: list[str], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _frontmatter(typ, title, description, tags, aliases, systems, signals) + body.rstrip() + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _body(case: Case, role: str) -> str:
    keyword, area, system, signal, action = case.domain
    code, symptom, phrase = case.symptom
    return f"""# Context

The {area} workflow reports {code} and {symptom} behavior around {signal}.
Operators use this {role} note when the {system} owner needs a deterministic
diagnosis path. The alternate wording is {phrase}.

# Diagnosis

Confirm the {signal} state, compare the latest {system} event, and identify the
customer impact before changing the {area} workflow.
The owner triage checklist records customer impact, escalation priority, and the
single accountable owner for this {area} incident.
Cross-document lookup should connect the runbook, decision record, and reference
facts for the {area} {symptom} workflow.

# Resolution

Apply the {action} recovery playbook and the diagnosis resolution checklist.
Then record the owner decision and update the incident log with the {area}
{symptom} finding.

# Atendimento

Para suporte, resolver incidente cliente prioridade usando o playbook de {area}
e confirmar o sintoma {symptom} antes da escalada.
"""


def _generate_vault(cases: list[Case]) -> None:
    if VAULT.exists():
        shutil.rmtree(VAULT)
    VAULT.mkdir(parents=True)
    _write_text(VAULT / "index.md", "# ApolloKairn Large Benchmark Vault\n")
    _write_text(VAULT / "log.md", "# Large Benchmark Log\n")
    _write_text(VAULT / "SCHEMA.md", "# Schema\n\n## Types\n\n- Runbook\n- Decision\n- Process\n- Reference\n")
    _write_text(VAULT / "AGENTS.md", "# Agent Instructions\n\nUse benchmark notes as deterministic fixtures.\n")

    for case in cases:
        if case.category == "no_answer":
            continue
        keyword, area, system, signal, action = case.domain
        code, symptom, phrase = case.symptom
        base_tags = [keyword, area, symptom.replace(" ", "-")]
        aliases = [phrase, f"{area} {action}", f"{code} {signal}"]
        systems = [keyword, system]
        signals = [code, symptom, signal]
        _write_note(
            VAULT / "knowledge" / f"{case.stem}-runbook.md",
            "Runbook",
            f"{area.title()} {code} {signal} runbook",
            f"Resolve {area} {symptom} incidents for {signal}.",
            base_tags,
            aliases,
            systems,
            signals,
            _body(case, "runbook"),
        )
        _write_note(
            VAULT / "decisions" / f"{case.stem}-decision.md",
            "Decision",
            f"{area.title()} {symptom} decision",
            f"Decision record for {area} {symptom} handling.",
            base_tags + ["decision"],
            aliases + [f"{area} decision"],
            systems,
            signals,
            _body(case, "decision"),
        )
        _write_note(
            VAULT / "references" / f"{case.stem}-reference.md",
            "Reference",
            f"{area.title()} {signal} reference",
            f"Reference facts for {area} {signal}.",
            base_tags + ["reference"],
            aliases + [f"{system} reference"],
            systems,
            signals,
            _body(case, "reference"),
        )

    for index in range(1, 76):
        domain = DOMAINS[(index + 3) % len(DOMAINS)]
        symptom = SYMPTOMS[(index + 5) % len(SYMPTOMS)]
        keyword, area, system, signal, action = domain
        code, symptom_word, phrase = symptom
        _write_note(
            VAULT / "distractors" / f"{area}-{_slug(symptom_word)}-{index:03d}.md",
            TYPES[index % len(TYPES)],
            f"Distractor {area} {symptom_word} {index:03d}",
            f"Nearby but non-relevant {area} fixture for benchmark contrast.",
            [keyword, "distractor", symptom_word.replace(" ", "-")],
            [f"{area} unrelated {action}", phrase],
            [keyword, system],
            [code, signal],
            f"""# Context

This distractor mentions {area}, {signal}, {action}, and {symptom_word}, but it
describes a separate maintenance exercise and is not the expected answer for the
large benchmark topics.

# Notes

Keep this note close enough to lexical matches that qrels must distinguish the
true incident from nearby operational language.
""",
        )


def _write_topics_and_qrels(cases: list[Case]) -> None:
    with TOPICS.open("w", encoding="utf-8", newline="\n") as topics, QRELS.open("w", encoding="utf-8", newline="\n") as qrels:
        for case in cases:
            topics.write(json.dumps(case.topic, ensure_ascii=False, sort_keys=True) + "\n")
            if case.category == "no_answer":
                continue
            qrels.write(f"{case.id}\tknowledge/{case.stem}-runbook.md\t3\n")
            if case.category == "filtered":
                continue
            qrels.write(f"{case.id}\tdecisions/{case.stem}-decision.md\t2\n")
            qrels.write(f"{case.id}\treferences/{case.stem}-reference.md\t1\n")


def _agent_task(case: Case) -> dict[str, object]:
    keyword, area, _system, _signal, action = case.domain
    _code, symptom, phrase = case.symptom
    task: dict[str, object] = {
        "id": f"task_{case.id.removeprefix('q_')}",
        "query_id": case.id,
        "question": case.query,
        "slice": case.category,
        "budget": case.topic["budget"],
        "expected_paths": [],
        "expected_facts": [],
        "expect_abstention": case.category == "no_answer",
    }
    if case.category == "no_answer":
        return task

    expected_paths = [f"knowledge/{case.stem}-runbook.md"]
    expected_facts = [phrase, f"{action} recovery playbook", "diagnosis resolution checklist"]
    if case.category == "cross_doc":
        task["budget"] = 1200
        expected_paths = [
            f"knowledge/{case.stem}-runbook.md",
            f"decisions/{case.stem}-decision.md",
            f"references/{case.stem}-reference.md",
        ]
        expected_facts = ["Cross-document lookup", "decision record", "reference facts"]
    elif case.category == "passage_budget":
        expected_facts = [f"{action} recovery playbook", "diagnosis resolution checklist"]
        task["mode"] = "passages"
    elif case.category == "noisy_query":
        task["ranker"] = "rrf"
    elif case.category == "filtered":
        task["type"] = "Runbook"
        task["system"] = keyword

    task["expected_paths"] = expected_paths
    task["expected_facts"] = expected_facts
    task["expect_abstention"] = False
    return task


def _write_agent_tasks(cases: list[Case]) -> None:
    TASKS.parent.mkdir(parents=True, exist_ok=True)
    with TASKS.open("w", encoding="utf-8", newline="\n") as handle:
        for case in cases:
            handle.write(json.dumps(_agent_task(case), ensure_ascii=False, sort_keys=True) + "\n")


def _write_golden() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "bench/run_eval.py",
            "--fixture",
            str(VAULT),
            "--topics",
            str(TOPICS),
            "--qrels",
            str(QRELS),
            "--min-recall",
            "0.7",
            "--min-mrr",
            "0.6",
            "--min-ndcg",
            "0.6",
            "--write-golden",
            str(GOLDEN),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)


def main() -> int:
    cases = _cases()
    _generate_vault(cases)
    _write_topics_and_qrels(cases)
    _write_agent_tasks(cases)
    _write_golden()
    print(
        "generated large fixture "
        f"notes={len(list(VAULT.rglob('*.md')))} "
        f"topics={len(cases)} "
        f"qrels={sum(1 for line in QRELS.read_text(encoding='utf-8').splitlines() if line.strip())} "
        f"tasks={sum(1 for line in TASKS.read_text(encoding='utf-8').splitlines() if line.strip())}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
