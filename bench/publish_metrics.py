from __future__ import annotations

import argparse
import json
import subprocess
import sys
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

RETRIEVAL_COMMAND = "python bench/run_eval.py --quiet --compare-golden bench/golden.json"
WRITEBACK_COMMAND = "python bench/run_writeback_eval.py --quiet --compare-golden bench/writeback/golden.json"

DEFAULT_HISTORY_METRICS = {
    "retrieval": ["recall_at_3", "ndcg_at_3", "context_reduction"],
    "writeback": ["decision_accuracy", "target_path_accuracy", "duplicate_avoidance_rate"],
}

NEUTRAL_METRICS = {"writeback_cases", "tests"}


def _run_json(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, *command],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"suites": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _suite(data: dict[str, Any], suite_id: str) -> dict[str, Any]:
    suites = data.setdefault("suites", [])
    for suite in suites:
        if suite.get("id") == suite_id:
            return suite
    suite: dict[str, Any] = {"id": suite_id, "current": {"metrics": []}, "history": []}
    suites.append(suite)
    return suite


def _metric(metrics: list[dict[str, Any]], metric_id: str) -> dict[str, Any]:
    for metric in metrics:
        if metric.get("id") == metric_id:
            return metric
    metric = {"id": metric_id, "label": {"en": metric_id, "pt": metric_id}, "format": "decimal", "precision": 4}
    metrics.append(metric)
    return metric


def _set_metric(metrics: list[dict[str, Any]], metric_id: str, value: int | float) -> None:
    metric = _metric(metrics, metric_id)
    metric["value"] = value


def _metric_value(metrics: list[dict[str, Any]], metric_id: str) -> int | float | None:
    for metric in metrics:
        if metric.get("id") == metric_id:
            value = metric.get("value")
            if isinstance(value, (int, float)):
                return value
    return None


def _upsert_history(history: list[dict[str, Any]], row: dict[str, Any]) -> int:
    key = (row.get("date"), row.get("label"))
    for index, existing in enumerate(history):
        if (existing.get("date"), existing.get("label")) == key:
            history[index] = row
            return index
    history.append(row)
    return len(history) - 1


def _trend(metric_id: str, delta: float) -> str:
    if delta == 0:
        return "flat"
    if metric_id in NEUTRAL_METRICS:
        return "changed"
    return "better" if delta > 0 else "worse"


def _add_deltas(suite: dict[str, Any], history_index: int) -> None:
    history = suite.get("history") or []
    metrics = suite.get("current", {}).get("metrics") or []
    previous = history[history_index - 1] if history_index > 0 else None
    for metric in metrics:
        metric.pop("delta", None)
        metric_id = metric.get("id")
        value = metric.get("value")
        if not previous or not isinstance(metric_id, str) or not isinstance(value, (int, float)):
            continue
        previous_value = previous.get(metric_id)
        if not isinstance(previous_value, (int, float)):
            continue
        delta = round(value - previous_value, 4)
        metric["delta"] = {
            "value": delta,
            "direction": "up" if delta > 0 else "down" if delta < 0 else "flat",
            "trend": _trend(metric_id, delta),
            "baseline_date": previous.get("date", ""),
            "baseline_label": previous.get("label", ""),
        }


def _update_retrieval(suite: dict[str, Any], payload: dict[str, Any], run_date: str, label: str) -> None:
    suite.setdefault("suite", {})
    suite["suite"]["command"] = RETRIEVAL_COMMAND
    suite.setdefault("history_metrics", DEFAULT_HISTORY_METRICS["retrieval"])
    corpus = deepcopy(payload["corpus"])

    current = suite.setdefault("current", {})
    current["corpus"] = corpus
    metrics = current.setdefault("metrics", [])
    _set_metric(metrics, "recall_at_3", payload["mean_recall_at_k"])
    _set_metric(metrics, "mrr_at_3", payload["mean_mrr_at_k"])
    _set_metric(metrics, "ndcg_at_3", payload["mean_ndcg_at_k"])
    _set_metric(metrics, "context_reduction", payload["context_reduction"])
    _set_metric(metrics, "comparison_reduction", payload["comparison"]["token_reduction"])

    row = {
        "date": run_date,
        "label": label,
        "recall_at_3": payload["mean_recall_at_k"],
        "mrr_at_3": payload["mean_mrr_at_k"],
        "ndcg_at_3": payload["mean_ndcg_at_k"],
        "context_reduction": payload["context_reduction"],
        "comparison_reduction": payload["comparison"]["token_reduction"],
        "corpus": corpus,
    }
    history_index = _upsert_history(suite.setdefault("history", []), row)
    _add_deltas(suite, history_index)


def _update_writeback(suite: dict[str, Any], payload: dict[str, Any], run_date: str, label: str) -> None:
    suite.setdefault("suite", {})
    suite["suite"]["command"] = WRITEBACK_COMMAND
    suite.setdefault("history_metrics", DEFAULT_HISTORY_METRICS["writeback"])

    metrics = suite.setdefault("current", {}).setdefault("metrics", [])
    _set_metric(metrics, "decision_accuracy", payload["decision_accuracy"])
    _set_metric(metrics, "target_path_accuracy", payload["target_path_accuracy"])
    _set_metric(metrics, "noop_accuracy", payload["noop_accuracy"])
    _set_metric(metrics, "conflict_detection_rate", payload["conflict_detection_rate"])
    _set_metric(metrics, "duplicate_avoidance_rate", payload["duplicate_avoidance_rate"])
    _set_metric(metrics, "writeback_cases", payload["cases"])

    row = {
        "date": run_date,
        "label": label,
        "decision_accuracy": payload["decision_accuracy"],
        "target_path_accuracy": payload["target_path_accuracy"],
        "noop_accuracy": payload["noop_accuracy"],
        "conflict_detection_rate": payload["conflict_detection_rate"],
        "duplicate_avoidance_rate": payload["duplicate_avoidance_rate"],
        "writeback_cases": payload["cases"],
    }
    history_index = _upsert_history(suite.setdefault("history", []), row)
    _add_deltas(suite, history_index)


def _update_legacy_fields(data: dict[str, Any], retrieval: dict[str, Any], tests: int | None) -> None:
    previous_metrics = data.get("current", {}).get("metrics", [])
    previous_tests = None
    if isinstance(previous_metrics, list):
        previous_tests = next((deepcopy(metric) for metric in previous_metrics if metric.get("id") == "tests"), None)

    data["current"] = deepcopy(retrieval.get("current", {}))
    if previous_tests:
        data.setdefault("current", {}).setdefault("metrics", []).append(previous_tests)
    if tests is not None or previous_tests:
        metrics = data.setdefault("current", {}).setdefault("metrics", [])
        current_tests = tests if tests is not None else previous_tests.get("value", 0)
        _set_metric(metrics, "tests", current_tests)
    data["suite"] = deepcopy(retrieval.get("suite", {}))
    data["history"] = deepcopy(retrieval.get("history", []))


def publish_metrics(
    input_path: Path,
    output_path: Path,
    run_date: str,
    retrieval_label: str,
    writeback_label: str,
    tests: int | None,
) -> dict[str, Any]:
    data = _load_json(input_path)
    retrieval_payload = _run_json(["bench/run_eval.py"])
    writeback_payload = _run_json(["bench/run_writeback_eval.py"])

    retrieval = _suite(data, "retrieval")
    writeback = _suite(data, "writeback")
    _update_retrieval(retrieval, retrieval_payload, run_date, retrieval_label)
    _update_writeback(writeback, writeback_payload, run_date, writeback_label)
    _update_legacy_fields(data, retrieval, tests)

    data["updated_at"] = run_date
    data["generated_by"] = "bench/publish_metrics.py"
    data["publish_command"] = "python bench/publish_metrics.py --output docs/data/benchmarks.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish Cairn benchmark metrics to docs/data/benchmarks.json.")
    parser.add_argument("--input", default=str(ROOT / "docs" / "data" / "benchmarks.json"))
    parser.add_argument("--output", default=str(ROOT / "docs" / "data" / "benchmarks.json"))
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--retrieval-label", default="BM25 + glossary aliases")
    parser.add_argument("--writeback-label", default="similarity-threshold-v1")
    parser.add_argument("--tests", type=int)
    args = parser.parse_args(argv)

    try:
        data = publish_metrics(
            input_path=Path(args.input),
            output_path=Path(args.output),
            run_date=args.date,
            retrieval_label=args.retrieval_label,
            writeback_label=args.writeback_label,
            tests=args.tests,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        "published benchmarks "
        f"suites={len(data.get('suites', []))} "
        f"updated_at={data.get('updated_at')} "
        f"output={Path(args.output).as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
