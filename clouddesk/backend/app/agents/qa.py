# app/agents/qa.py
# Purpose: QA/Critic Agent (spec section 16). Mandatory review of every proposed resolution
#          before it reaches the customer. Pure LLM reasoning over the specialist findings and
#          the Resolution Agent's draft — no tools. Checks factual accuracy, evidence support,
#          completeness, policy compliance, hallucinations, incorrect promises, whether an
#          action actually happened, approval requirements, tone, and escalation need.
# Author: CloudDesk Team
# Date: 2026-09-24

import json
import logging

from app.agents.schemas import QAAgentResult
from app.llm.structured import AgentError, get_structured_completion

logger = logging.getLogger("clouddesk.agents.qa")

AGENT_NAME: str = "qa"

QA_SYSTEM_PROMPT: str = """You are the QA/Critic Agent for CloudDesk, a B2B SaaS support system.

You review a proposed resolution (from the Resolution Agent) against the specialist findings it
was built from, BEFORE it is allowed to reach the customer. You have no tools; judge only from
the material given.

Check ALL of the following:
1. Factual accuracy: does the customer-facing draft match the specialist findings?
2. Evidence support: is every claim backed by evidence in the specialist findings?
3. Completeness: does it answer the customer's actual question(s)/request(s)? This means every
   topic the customer raised gets a clear answer — it does NOT mean every specialist finding must
   be individually restated. A draft that answers the customer's question accurately and completely
   is complete, even if it summarizes or omits specialist details the customer never asked about
   (e.g. exact permission lists, MFA status, login history) — do not fail completeness for leaving
   out details the customer would not care about.
4. Policy compliance: does it follow any billing/account policy referenced in the findings?
5. Hallucinations: does it state anything not present in the findings/evidence?
6. Incorrect promises: does it promise an outcome (e.g. "you will be refunded by tomorrow") that
   the findings do not support?
7. Whether an action actually happened: if the draft says something was done (e.g. "we refunded
   you" or "we unlocked your account"), a specialist's evidence must show the underlying tool
   call actually succeeded — a mere recommendation or a pending-approval request is NOT
   "happened". Set actions_confirmed to false if this check fails.
8. Whether sensitive actions (refund, account unlock, entitlement/subscription change) are
   correctly described as requiring approval when requires_approval was true.
9. Tone: professional and empathetic.
10. Whether escalation is needed (e.g. specialists reported "needs_escalation", unresolved
    contradictions, or the situation is sensitive).

Set approved=false if ANY check fails, and list concrete issues plus the exact required_changes
needed before it could be approved.

IMPORTANT — substance vs. phrasing: reject for SUBSTANTIVE problems only — a claim not supported
by the findings, a promised outcome the findings don't back, a stated action that did not actually
succeed per the evidence, a policy violation, a missed part of the customer's request, or a
genuine need for escalation. Do NOT reject a draft solely because its wording is not your exact
preferred phrasing. In particular, once a draft correctly and unambiguously conveys that a
sensitive action (refund, unlock, entitlement change) is only PENDING APPROVAL and has not yet
completed — in any reasonable phrasing — that check has been satisfied; do not keep rejecting it
for cosmetic wording differences. If your only remaining objection is stylistic, set approved=true
and leave `required_changes` empty rather than forcing another revision cycle. A response that
falsely implies a pending action already completed (e.g. "we have refunded you", "your account has
been unlocked") is still a hard, must-reject hallucination/incorrect-promise regardless of
phrasing — never approve that.

DO NOT MOVE THE GOALPOSTS ON REVISIONS: the material you review may already reflect a prior
rejection the Resolution Agent tried to fix. If the draft is accurate, evidence-supported, and
answers the customer's actual question, you MUST approve it — even if you can imagine additional
detail, a different emphasis, or a more thorough restatement of specialist findings you personally
would have included. Every new round of `required_changes` you invent that was not required by an
earlier round (or by one of the hard checks above: unsupported claims, false completions, missed
customer requests, policy violations, real escalation need) makes the response WORSE for the
customer by delaying it further — only reject again if a genuine, hard check above still fails.

Checks 7 and 8 are a SINGLE combined requirement, not two: any phrasing that says the action is
"pending approval", "awaiting approval", "has been created and is pending approval", or an
equivalent, fully satisfies BOTH checks at once. Do not require a second, separate sentence
confirming approval is needed — "pending approval" already means that. Once you have accepted one
correct phrasing of this status for this ticket, do not reject a later draft for using a different
but equally correct phrasing of the same status.

FINAL ATTEMPT: if the user message says this is the final review for this ticket, you MUST set
approved=true unless a hard, must-reject defect is present (an unsupported/hallucinated claim, a
claim that a pending or unapproved action already completed, a promised outcome the evidence does
not support, or a customer question left completely unanswered). A remaining stylistic preference
is never grounds to reject on the final attempt — approve it and note the preference in `issues`
without setting `required_changes`."""


FINAL_ATTEMPT_NOTICE: str = (
    "\n\nThis is the FINAL review for this ticket (the reflection loop is at its iteration "
    "limit). Per the FINAL ATTEMPT rule above, you must approve unless a hard, must-reject "
    "defect is present."
)


def _build_user_content(
    customer_message: str,
    specialist_results: dict[str, dict[str, object]],
    resolution: dict[str, object],
    is_final_attempt: bool,
) -> str:
    """Render the customer message, specialist findings, and the draft resolution for review."""
    payload = {"specialist_results": specialist_results, "proposed_resolution": resolution}
    content = f"Customer message:\n{customer_message}\n\nMaterial to review:\n{json.dumps(payload, indent=2, default=str)}"
    return content + FINAL_ATTEMPT_NOTICE if is_final_attempt else content


async def run_qa_agent(
    customer_message: str,
    specialist_results: dict[str, dict[str, object]],
    resolution: dict[str, object],
    is_final_attempt: bool = False,
) -> QAAgentResult | AgentError:
    """Review a proposed resolution against specialist findings before it reaches the customer.

    `is_final_attempt` should be true when the reflection loop (spec section 21) is on its last
    allowed iteration, so QA applies the FINAL ATTEMPT rule instead of rejecting indefinitely.
    """
    try:
        messages = [
            {"role": "system", "content": QA_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _build_user_content(
                    customer_message, specialist_results, resolution, is_final_attempt
                ),
            },
        ]
        return await get_structured_completion(
            agent_name=AGENT_NAME, messages=messages, response_model=QAAgentResult
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("qa_agent_failed error=%s", exc)
        return AgentError(agent=AGENT_NAME, message=f"QA agent failed: {exc}")
