# tests/test_approval_live_integration.py
# Purpose: ONE real end-to-end proof of the Phase 5 human-in-the-loop path (spec section 22,
#          Scenario B): a real LLM-backed support workflow run pauses on a genuine duplicate-
#          payment refund recommendation, the real HTTP approval API approves it, and the paused
#          workflow resumes to completion — against the real database and the real compiled
#          graph/checkpointer, no mocks. Marked `integration` and excluded from the default
#          `pytest` run (see pytest.ini addopts), same policy as
#          tests/test_graph_live_integration.py. Run explicitly with:
#              pytest -m integration tests/test_approval_live_integration.py -v -s
# Author: CloudDesk Team
# Date: 2026-09-24

from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.graph import get_support_graph, run_support_workflow
from app.main import app
from app.models.approval import ApprovalRequest
from app.models.enums import PaymentStatus
from tests.factories import create_customer_with_account, create_org_and_plan, create_payment

pytestmark = pytest.mark.integration

_PERIOD = datetime(2026, 9, 1, tzinfo=timezone.utc)


async def test_full_pause_approve_resume_live(committed_session: AsyncSession) -> None:
    """Real LLM run pauses on a duplicate-charge refund recommendation; the real approval API
    approves it; the paused workflow resumes and the payment is genuinely marked REFUNDED.
    """
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    subscription_id = customer.subscriptions[0].id
    payment_a = await create_payment(committed_session, customer, subscription_id, 49, PaymentStatus.SUCCEEDED, _PERIOD)
    await create_payment(committed_session, customer, subscription_id, 49, PaymentStatus.SUCCEEDED, _PERIOD)
    await committed_session.commit()

    paused_state = await run_support_workflow(
        customer_id=str(customer.id), customer_message="I was charged twice for my subscription, please refund me."
    )
    print("\n--- LIVE APPROVAL RUN: PAUSED STATE ---")
    for key, value in paused_state.items():
        print(f"{key}: {value}")

    assert paused_state["human_approval_required"] is True
    thread_id = paused_state["thread_id"]

    result = await committed_session.execute(
        select(ApprovalRequest).where(ApprovalRequest.thread_id == thread_id)
    )
    approval_requests = result.scalars().all()
    assert approval_requests, "expected a persisted ApprovalRequest for the paused thread"
    action_id = approval_requests[0].id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            f"/api/v1/approvals/{action_id}/approve", json={"actor": "live_integration_test"}
        )
    print("--- APPROVE RESPONSE ---")
    print(response.status_code, response.json())

    assert response.status_code == 200
    body = response.json()
    assert body["workflow_resumed"] is True
    assert body["final_response"]

    await committed_session.refresh(payment_a)
    assert payment_a.status == PaymentStatus.REFUNDED

    # Clean up this run's checkpointer thread so it doesn't linger across test invocations.
    graph = get_support_graph()
    await graph.checkpointer.adelete_thread(thread_id)
