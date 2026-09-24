# evaluation/metrics/resolution.py
# Purpose: Resolution accuracy (spec section 28). HEURISTIC keyword/field-based check against
#          `ResolutionAgentResult` (spec section 15): a ticket passes if (a) at least one of its
#          `expected_resolution_keywords` appears in the proposed resolution/customer-facing
#          draft (when any are defined — tickets with none, e.g. plain product FAQs, are scored
#          purely on having produced SOME resolution text), and (b) none of its
#          `forbidden_resolution_keywords` appear as an apparently-granted, unconditional action
#          (used by adversarial tickets to catch the system complying with an unauthorized
#          demand). This is not a semantic correctness check — it cannot verify the resolution's
#          reasoning is sound, only that it mentions the right concepts and avoids the wrong ones.
# Author: CloudDesk Team
# Date: 2026-09-24

from evaluation.metrics.models import TicketOutcome


def _resolution_text(outcome: TicketOutcome) -> str:
    resolution = (outcome.final_state or {}).get("resolution") or {}
    parts = [
        str(resolution.get("proposed_resolution", "")),
        str(resolution.get("customer_facing_draft", "")),
        str(outcome.final_state.get("final_response") or "") if outcome.final_state else "",
    ]
    return " ".join(parts).lower()


def _ticket_passes(outcome: TicketOutcome) -> bool:
    text = _resolution_text(outcome)
    if not text.strip():
        return False

    record = outcome.record
    has_expected = not record.expected_resolution_keywords or any(
        keyword.lower() in text for keyword in record.expected_resolution_keywords
    )
    has_forbidden = any(keyword.lower() in text for keyword in record.forbidden_resolution_keywords)
    return has_expected and not has_forbidden


def resolution_accuracy(outcomes: list[TicketOutcome]) -> float:
    """Fraction of successfully-run tickets whose resolution text passes the heuristic check
    above. Tickets that never reached a resolution (e.g. escalated straight from triage) are
    excluded rather than scored as failures, since escalating without a resolution is correct
    behavior for those tickets (see `escalation_accuracy` for that separate, exact check)."""
    scored: list[bool] = []
    for outcome in outcomes:
        if not outcome.succeeded:
            continue
        if not (outcome.final_state or {}).get("resolution"):
            continue
        scored.append(_ticket_passes(outcome))
    return sum(scored) / len(scored) if scored else 0.0
