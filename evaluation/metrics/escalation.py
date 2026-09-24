# evaluation/metrics/escalation.py
# Purpose: Escalation accuracy (spec section 28) — the one metric the Phase 8 brief flags as
#          EXACTLY and precisely measurable: whether `SupportState.escalation_required` matches
#          `DatasetRecord.expected_escalation` exactly, per ticket. False-positive tickets
#          (`is_false_positive=True`) are exactly the case this metric is designed to catch the
#          system failing at: `expected_escalation=False` for them, so an over-eager escalation
#          on legitimate heavy usage counts as a wrong answer here just like any other mismatch.
# Author: CloudDesk Team
# Date: 2026-09-24

from evaluation.metrics.models import TicketOutcome


def escalation_accuracy(outcomes: list[TicketOutcome]) -> float:
    """Fraction of successfully-run tickets where actual escalation exactly matched expected."""
    scored = [
        bool(o.final_state.get("escalation_required")) == o.record.expected_escalation
        for o in outcomes
        if o.succeeded
    ]
    return sum(scored) / len(scored) if scored else 0.0


def false_positive_escalation_rate(outcomes: list[TicketOutcome]) -> float:
    """Of tickets labeled `is_false_positive=True` (legitimate-looking-unusual activity), the
    fraction that were WRONGLY escalated anyway — spec section 6's explicit requirement that
    "the system must not escalate every unusual event," isolated as its own number since it is
    the specific failure mode false-positive tickets exist to catch."""
    false_positive_outcomes = [o for o in outcomes if o.succeeded and o.record.is_false_positive]
    if not false_positive_outcomes:
        return 0.0
    wrongly_escalated = sum(1 for o in false_positive_outcomes if o.final_state.get("escalation_required"))
    return wrongly_escalated / len(false_positive_outcomes)
