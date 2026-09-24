# evaluation/metrics/routing.py
# Purpose: Intent classification accuracy and routing accuracy (spec section 28's first two
#          metrics). Both are scored as Jaccard similarity (|intersection| / |union|) between the
#          ground-truth set and the actual set the real run produced, averaged over all
#          successfully-run tickets. Jaccard (rather than exact-set-match) is chosen and
#          documented here because the Triage Agent legitimately may return a superset/subset of
#          intents/agents that is still substantively correct (e.g. adding "account" alongside
#          "technical" for an entitlement issue) — exact match would harshly penalize reasonable
#          near-misses that set-overlap scoring rewards proportionally.
# Author: CloudDesk Team
# Date: 2026-09-24

from evaluation.metrics.models import TicketOutcome


def jaccard_similarity(expected: list[str], actual: list[str]) -> float:
    """|intersection| / |union| of two label sets; 1.0 when both are empty (nothing to disagree on)."""
    expected_set, actual_set = set(expected), set(actual)
    if not expected_set and not actual_set:
        return 1.0
    union = expected_set | actual_set
    if not union:
        return 1.0
    return len(expected_set & actual_set) / len(union)


def intent_classification_accuracy(outcomes: list[TicketOutcome]) -> float:
    """Mean Jaccard similarity between `DatasetRecord.expected_intents` and the real run's
    final `intents`, over every ticket that actually produced a final state."""
    scores = [
        jaccard_similarity(o.record.expected_intents, o.final_state.get("intents", []))
        for o in outcomes
        if o.succeeded
    ]
    return sum(scores) / len(scores) if scores else 0.0


def routing_accuracy(outcomes: list[TicketOutcome]) -> float:
    """Mean Jaccard similarity between `DatasetRecord.expected_required_agents` and the real
    run's final `required_agents` (which specialists the dynamic router actually fanned out to)."""
    scores = [
        jaccard_similarity(o.record.expected_required_agents, o.final_state.get("required_agents", []))
        for o in outcomes
        if o.succeeded
    ]
    return sum(scores) / len(scores) if scores else 0.0
