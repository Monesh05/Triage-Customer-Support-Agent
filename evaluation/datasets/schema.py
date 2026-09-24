# evaluation/datasets/schema.py
# Purpose: Pydantic schema for one synthetic evaluation ticket record (spec section 28), plus
#          the fixed category/agent-name constants the dataset, generator, and metrics modules
#          all share. Kept dependency-free (no backend `app.*` imports) so the schema — and the
#          dataset it validates — can be unit-tested without a database or `evaluation/__init__`'s
#          sys.path shim having run.
# Author: CloudDesk Team
# Date: 2026-09-24

from typing import Literal

from pydantic import BaseModel, Field

# The 10 categories spec section 28 requires evaluation coverage for.
CATEGORY_BILLING: str = "billing"
CATEGORY_ACCOUNT: str = "account"
CATEGORY_TECHNICAL: str = "technical"
CATEGORY_PRODUCT: str = "product"
CATEGORY_MULTI_INTENT: str = "multi-intent"
CATEGORY_AMBIGUOUS: str = "ambiguous"
CATEGORY_ESCALATION: str = "escalation"
CATEGORY_FALSE_POSITIVE: str = "false-positive"
CATEGORY_POLICY_SENSITIVE: str = "policy-sensitive"
CATEGORY_ADVERSARIAL: str = "adversarial"

REQUIRED_CATEGORIES: tuple[str, ...] = (
    CATEGORY_BILLING,
    CATEGORY_ACCOUNT,
    CATEGORY_TECHNICAL,
    CATEGORY_PRODUCT,
    CATEGORY_MULTI_INTENT,
    CATEGORY_AMBIGUOUS,
    CATEGORY_ESCALATION,
    CATEGORY_FALSE_POSITIVE,
    CATEGORY_POLICY_SENSITIVE,
    CATEGORY_ADVERSARIAL,
)

CategoryLiteral = Literal[
    "billing",
    "account",
    "technical",
    "product",
    "multi-intent",
    "ambiguous",
    "escalation",
    "false-positive",
    "policy-sensitive",
    "adversarial",
]

IntentLiteral = Literal["billing", "account", "technical", "product", "other"]
AgentNameLiteral = Literal["billing", "account", "technical", "product", "escalation"]
PriorityLiteral = Literal["low", "medium", "high", "urgent"]

MIN_DATASET_SIZE: int = 100


class DatasetRecord(BaseModel):
    """One synthetic ground-truth-labeled support ticket (spec section 28).

    Ground-truth fields are deliberately a mix of exact expectations (e.g.
    `expected_escalation`) and softer signals used by heuristic metrics (e.g.
    `expected_resolution_keywords`) — see `evaluation/metrics/*` for exactly how each field is
    scored, and which scores are exact vs. heuristic.
    """

    ticket_id: str = Field(description="Stable id for this dataset record, e.g. 'billing-003'.")
    category: CategoryLiteral
    customer_id: str = Field(description="A real seeded `customers.id` UUID (see data/seed).")
    customer_message: str

    expected_intents: list[IntentLiteral]
    expected_required_agents: list[AgentNameLiteral]
    expected_priority: PriorityLiteral
    expected_escalation: bool
    is_false_positive: bool = Field(
        default=False,
        description="True if this ticket describes unusual-but-legitimate activity that the "
        "system must NOT over-escalate (spec section 6/23's false-positive scenarios).",
    )
    expect_qa_approval: bool | None = Field(
        default=None,
        description="Expected value of QAAgentResult.approved, when this ticket was designed "
        "specifically to test QA behavior (ambiguous/policy-sensitive/adversarial tickets). "
        "None means no strong expectation is asserted for this ticket.",
    )
    expected_resolution_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords (any-one-of) expected to appear in the resolution's proposed "
        "action / customer-facing draft if the issue was investigated correctly, e.g. "
        "['refund'] for a duplicate-charge ticket. Heuristic, not exact — see "
        "evaluation/metrics/resolution.py.",
    )
    forbidden_resolution_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords that should NOT appear as an unconditionally-granted action in "
        "the resolution (used by adversarial tickets to catch the system complying with an "
        "unauthorized/oversized demand), e.g. a resolution stating a $5,000 refund was "
        "processed outright.",
    )
    notes: str = Field(default="", description="Human-readable rationale for this ticket's labels.")
