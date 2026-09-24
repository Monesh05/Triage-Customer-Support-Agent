# evaluation/metrics/models.py
# Purpose: The shared per-ticket data shape every metric function in this package consumes —
#          one dataset record's ground truth plus what the real evaluation run actually observed
#          (final SupportState fields, the AgentRun trace, latency, and any ticket-level failure).
#          Deliberately dependency-free (no backend `app.*` imports, no DB/LLM calls) so metric
#          functions can be unit-tested against hand-built `TicketOutcome` instances (spec Phase
#          8 brief's testing requirement) without running the real graph.
# Author: CloudDesk Team
# Date: 2026-09-24

from typing import Any

from pydantic import BaseModel, Field

from evaluation.datasets.schema import DatasetRecord


class AgentRunView(BaseModel):
    """The subset of an `AgentRun` row (app.models.observability.AgentRun) a metric needs.

    Field names mirror the ORM model directly so `run_eval.py` can build one of these straight
    from `AgentRun.__dict__`-style attribute access without any renaming.
    """

    agent_name: str
    status: str
    duration_ms: int
    iteration: int | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class TicketOutcome(BaseModel):
    """Ground truth (`record`) plus what one real evaluation run actually observed for it."""

    record: DatasetRecord
    final_state: dict[str, Any] | None = Field(
        default=None, description="The workflow's final SupportState, as a plain dict, or None "
        "if the ticket-level run itself raised (see `run_error`)."
    )
    trace: list[AgentRunView] = Field(default_factory=list)
    total_latency_ms: float | None = None
    run_error: str | None = Field(
        default=None, description="Set when running this ticket through the real workflow raised "
        "an unexpected exception; the ticket is excluded from state-dependent metrics but still "
        "counted (as a failure) in the run summary."
    )

    @property
    def succeeded(self) -> bool:
        return self.run_error is None and self.final_state is not None
