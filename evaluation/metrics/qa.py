# evaluation/metrics/qa.py
# Purpose: QA accuracy and hallucination rate (spec section 28). QA accuracy is HEURISTIC:
#          scored only against the subset of tickets with a defined `expect_qa_approval` label
#          (ambiguous/policy-sensitive/adversarial tickets designed specifically to probe QA
#          behavior, spec section 16) — did `QAAgentResult.approved` end up matching that
#          expectation. Tickets with no such label are excluded rather than guessed at.
#          Hallucination rate is measured EXACTLY as-is but is an honest proxy, not an
#          independent oracle: it is the fraction of tickets where the QA Agent itself flagged
#          `hallucination_detected`, i.e. "how often does QA's own hallucination check fire",
#          not "how often did the system actually hallucinate" (that would need human review of
#          every response against ground truth, out of scope for this phase).
# Author: CloudDesk Team
# Date: 2026-09-24

from evaluation.metrics.models import TicketOutcome


def _final_qa_result(outcome: TicketOutcome) -> dict[str, object] | None:
    return (outcome.final_state or {}).get("qa_result") if outcome.final_state else None


def qa_accuracy(outcomes: list[TicketOutcome]) -> float:
    """Fraction of QA-expectation-labeled tickets where `qa_result.approved` matched
    `DatasetRecord.expect_qa_approval`. See module docstring: heuristic, and only meaningful
    for the subset of tickets that carry this label."""
    scored: list[bool] = []
    for outcome in outcomes:
        if not outcome.succeeded or outcome.record.expect_qa_approval is None:
            continue
        qa_result = _final_qa_result(outcome)
        if qa_result is None:
            scored.append(False)
            continue
        scored.append(bool(qa_result.get("approved")) == outcome.record.expect_qa_approval)
    return sum(scored) / len(scored) if scored else 0.0


def hallucination_rate(outcomes: list[TicketOutcome]) -> float:
    """Fraction of successfully-run tickets where QA's own `hallucination_detected` flag was
    True at any reflection iteration (see module docstring for what this proxy does/does not
    measure)."""
    succeeded = [o for o in outcomes if o.succeeded]
    if not succeeded:
        return 0.0
    flagged = 0
    for outcome in succeeded:
        qa_result = _final_qa_result(outcome)
        if qa_result and qa_result.get("hallucination_detected"):
            flagged += 1
    return flagged / len(succeeded)
