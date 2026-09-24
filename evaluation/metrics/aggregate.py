# evaluation/metrics/aggregate.py
# Purpose: Computes every spec section 28 metric across a full evaluation run, both overall and
#          broken down per category, and reports how many tickets errored outright (a ticket-
#          level failure is never silently dropped from the run summary, only from metrics that
#          require a final state). This is the single function `run_eval.py` calls after
#          collecting all `TicketOutcome`s.
# Author: CloudDesk Team
# Date: 2026-09-24

from typing import Any

from evaluation.datasets.schema import REQUIRED_CATEGORIES
from evaluation.metrics.escalation import escalation_accuracy, false_positive_escalation_rate
from evaluation.metrics.latency import average_iterations, average_latency_ms
from evaluation.metrics.models import TicketOutcome
from evaluation.metrics.qa import hallucination_rate, qa_accuracy
from evaluation.metrics.resolution import resolution_accuracy
from evaluation.metrics.routing import intent_classification_accuracy, routing_accuracy
from evaluation.metrics.tool_calls import tool_call_accuracy

PERCENTAGE_METRIC_NAMES: tuple[str, ...] = (
    "intent_classification_accuracy",
    "routing_accuracy",
    "tool_call_accuracy",
    "resolution_accuracy",
    "qa_accuracy",
    "escalation_accuracy",
    "hallucination_rate",
    "false_positive_escalation_rate",
)


def compute_metrics(outcomes: list[TicketOutcome]) -> dict[str, Any]:
    """Compute every spec section 28 metric over one list of `TicketOutcome`s (all tickets, or
    a single category's subset). Returns a flat dict of metric_name -> float, plus ticket counts."""
    succeeded = sum(1 for o in outcomes if o.succeeded)
    failed = len(outcomes) - succeeded
    return {
        "ticket_count": len(outcomes),
        "succeeded_count": succeeded,
        "failed_count": failed,
        "intent_classification_accuracy": intent_classification_accuracy(outcomes),
        "routing_accuracy": routing_accuracy(outcomes),
        "tool_call_accuracy": tool_call_accuracy(outcomes),
        "resolution_accuracy": resolution_accuracy(outcomes),
        "qa_accuracy": qa_accuracy(outcomes),
        "escalation_accuracy": escalation_accuracy(outcomes),
        "false_positive_escalation_rate": false_positive_escalation_rate(outcomes),
        "hallucination_rate": hallucination_rate(outcomes),
        "average_latency_ms": average_latency_ms(outcomes),
        "average_iterations": average_iterations(outcomes),
    }


def compute_full_report(outcomes: list[TicketOutcome]) -> dict[str, Any]:
    """Overall metrics plus a per-category breakdown, covering every required category (spec
    section 28) even if a given run happened to include zero tickets for one (e.g. `--categories`
    filtering) — that category is reported with zero counts rather than omitted."""
    by_category: dict[str, list[TicketOutcome]] = {category: [] for category in REQUIRED_CATEGORIES}
    for outcome in outcomes:
        by_category.setdefault(outcome.record.category, []).append(outcome)

    return {
        "overall": compute_metrics(outcomes),
        "by_category": {category: compute_metrics(items) for category, items in by_category.items()},
    }
