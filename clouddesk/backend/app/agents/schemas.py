# app/agents/schemas.py
# Purpose: Pydantic v2 structured-output schemas for every Phase 3 agent, matching the example
#          JSON shapes in spec sections 9 (Triage), 10 (Billing), 11 (Account), 12 (Technical),
#          13 (Product), 15 (Resolution), 16 (QA/Critic), and 17 (Escalation).
# Author: CloudDesk Team
# Date: 2026-09-24

from typing import Literal

from pydantic import BaseModel, Field

IntentLiteral = Literal["billing", "account", "technical", "product", "other"]
AgentNameLiteral = Literal["billing", "account", "technical", "product", "escalation"]
PriorityLiteral = Literal["low", "medium", "high", "urgent"]
SentimentLiteral = Literal["frustrated", "angry", "confused", "neutral", "satisfied"]
InvestigationStatusLiteral = Literal["resolved", "unresolved", "needs_escalation"]


class TriageResult(BaseModel):
    """Triage Agent output (spec section 9). Classification only — never a resolution."""

    intents: list[IntentLiteral]
    priority: PriorityLiteral
    sentiment: SentimentLiteral
    required_agents: list[AgentNameLiteral]
    reason: str


class Finding(BaseModel):
    """A single investigated fact, grounded in tool evidence."""

    fact: str


class RecommendedAction(BaseModel):
    """A proposed action a specialist agent surfaces but does not itself carry out unilaterally."""

    action: str
    amount: float | None = None
    requires_approval: bool


class BillingAgentResult(BaseModel):
    """Billing Agent output (spec section 10)."""

    status: InvestigationStatusLiteral
    findings: list[Finding]
    recommended_actions: list[RecommendedAction]
    evidence: list[str] = Field(
        description="Concrete record identifiers (payment/invoice ids) the findings rely on."
    )


class AccountAgentResult(BaseModel):
    """Account Agent output (spec section 11)."""

    status: InvestigationStatusLiteral
    findings: list[Finding]
    recommended_actions: list[RecommendedAction]
    evidence: list[str] = Field(
        description="Concrete record identifiers/values (account id, subscription/entitlement "
        "plan names) the findings rely on."
    )


class TechnicalAgentResult(BaseModel):
    """Technical Support Agent output (spec section 12): hypothesis + evidence."""

    hypothesis: str
    status: InvestigationStatusLiteral
    evidence: list[str]
    recommended_actions: list[RecommendedAction]


class ProductSource(BaseModel):
    """A single retrieved source citation for a Product Agent answer."""

    product_id: str
    name: str


class ProductAgentResult(BaseModel):
    """Product Agent output (spec section 13). Must cite only what was actually retrieved."""

    answer: str
    sources: list[ProductSource]
    grounded: bool = Field(
        description="True only if `answer` is based on retrieved `sources`; false if no "
        "matching product docs were found and the answer says so rather than inventing content."
    )


class ResolutionAgentResult(BaseModel):
    """Resolution Agent output (spec section 15): synthesis only, no invented facts."""

    summary: str
    issues_identified: list[str]
    proposed_resolution: str
    customer_facing_draft: str
    unresolved_questions: list[str]
    requires_approval: bool


class QAAgentResult(BaseModel):
    """QA/Critic Agent output (spec section 16)."""

    approved: bool
    issues: list[str]
    required_changes: list[str]
    evidence_supported: bool
    hallucination_detected: bool
    policy_compliant: bool
    actions_confirmed: bool = Field(
        description="False if the draft claims an action happened that no tool result confirms."
    )
    escalation_needed: bool


class EscalationAgentResult(BaseModel):
    """Escalation Agent output (spec section 17): a structured internal handoff, never a bare
    'contact support' message."""

    customer: str
    issue: str
    intent: list[IntentLiteral]
    priority: PriorityLiteral
    investigation_performed: list[str]
    evidence: list[str]
    actions_attempted: list[str]
    unresolved_questions: list[str]
    recommended_human_action: str
    conversation_history: list[str]
