# evaluation/metrics/latency.py
# Purpose: Average latency and average number of agent iterations (spec section 28) — both
#          measured EXACTLY from real data: latency from each ticket's total wall-clock duration
#          (sum of its `AgentRun.duration_ms` trace rows, i.e. actual LLM/tool call time, not
#          process overhead), iterations from the final `SupportState.iteration` counter the
#          resolution/QA reflection loop (spec section 21) actually reached.
# Author: CloudDesk Team
# Date: 2026-09-24

from evaluation.metrics.models import TicketOutcome


def average_latency_ms(outcomes: list[TicketOutcome]) -> float:
    """Mean total per-ticket latency in milliseconds, summed across that ticket's whole
    AgentRun trace (every specialist/resolution/qa/escalation call it made)."""
    values = [o.total_latency_ms for o in outcomes if o.succeeded and o.total_latency_ms is not None]
    return sum(values) / len(values) if values else 0.0


def average_iterations(outcomes: list[TicketOutcome]) -> float:
    """Mean value of the final `SupportState.iteration` (resolution/QA reflection loop count,
    spec section 21; MAX_ITERATIONS = 3) across successfully-run tickets."""
    values = [o.final_state.get("iteration", 0) for o in outcomes if o.succeeded]
    return sum(values) / len(values) if values else 0.0
