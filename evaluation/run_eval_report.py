# evaluation/run_eval_report.py
# Purpose: Per-ticket result serialization and the human-readable stdout summary for
#          run_eval.py — split out purely to keep run_eval.py under this codebase's
#          300-line-per-file guideline.
# Author: CloudDesk Team
# Date: 2026-09-24

from typing import Any

from evaluation.metrics.models import TicketOutcome

METRIC_DISPLAY_ORDER: tuple[str, ...] = (
    "intent_classification_accuracy",
    "routing_accuracy",
    "tool_call_accuracy",
    "resolution_accuracy",
    "qa_accuracy",
    "escalation_accuracy",
    "false_positive_escalation_rate",
    "hallucination_rate",
    "average_latency_ms",
    "average_iterations",
)


def ticket_to_result_dict(outcome: TicketOutcome) -> dict[str, Any]:
    """One ticket's row in the results.json `tickets` array: dataset labels plus the real
    observed outcome, small enough to eyeball or feed a future dashboard (Phase 9)."""
    state = outcome.final_state or {}
    qa_result = state.get("qa_result") or {}
    return {
        "ticket_id": outcome.record.ticket_id,
        "category": outcome.record.category,
        "customer_id": outcome.record.customer_id,
        "succeeded": outcome.succeeded,
        "run_error": outcome.run_error,
        "latency_ms": outcome.total_latency_ms,
        "iteration": state.get("iteration"),
        "intents": state.get("intents"),
        "required_agents": state.get("required_agents"),
        "escalation_required": state.get("escalation_required"),
        "human_approval_required": state.get("human_approval_required"),
        "qa_approved": qa_result.get("approved"),
        "hallucination_detected": qa_result.get("hallucination_detected"),
        "expected_escalation": outcome.record.expected_escalation,
        "expected_intents": outcome.record.expected_intents,
    }


def _format_metric(name: str, value: float) -> str:
    if name in ("average_latency_ms",):
        return f"{name}: {value:.0f}ms"
    if name in ("average_iterations",):
        return f"{name}: {value:.2f}"
    return f"{name}: {value * 100:.1f}%"


def _print_metrics_block(title: str, metrics: dict[str, Any]) -> None:
    print(f"\n{title} (n={metrics['ticket_count']}, ok={metrics['succeeded_count']}, "
          f"failed={metrics['failed_count']})")
    for name in METRIC_DISPLAY_ORDER:
        print(f"  {_format_metric(name, metrics[name])}")


def print_summary(document: dict[str, Any]) -> None:
    """Print the overall + per-category metric report to stdout."""
    metadata = document["run_metadata"]
    print("\n=== CloudDesk Evaluation Results ===")
    print(f"Timestamp: {metadata['timestamp']}  Model: {metadata['model']} ({metadata['llm_provider']})")
    print(f"Dataset: {metadata['dataset_path']}  Tickets run: {metadata['dataset_size']}")

    _print_metrics_block("OVERALL", document["metrics"]["overall"])
    for category, metrics in document["metrics"]["by_category"].items():
        if metrics["ticket_count"] > 0:
            _print_metrics_block(f"Category: {category}", metrics)
    print()
