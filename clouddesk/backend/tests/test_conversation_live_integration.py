# tests/test_conversation_live_integration.py
# Purpose: ONE real end-to-end proof of the Phase 9 customer-facing chat API (spec section 25):
#          a real HTTP POST to /api/v1/conversations starts a genuine LLM-backed support-workflow
#          run against the real database, and polling GET /api/v1/conversations/{thread_id}
#          against the real (non-overridden) app observes the run's real progress and eventual
#          completion — no mocks anywhere in this test. Marked `integration` and excluded from the
#          default `pytest` run (see pytest.ini addopts), same policy as every other phase's one
#          live test (tests/test_graph_live_integration.py, tests/test_approval_live_integration.py).
#          Run explicitly with:
#              pytest -m integration tests/test_conversation_live_integration.py -v -s
# Author: CloudDesk Team
# Date: 2026-09-24

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from tests.conftest import auth_headers
from tests.factories import create_customer_with_account, create_org_and_plan

pytestmark = pytest.mark.integration

_POLL_TIMEOUT_SECONDS = 90.0
_POLL_INTERVAL_SECONDS = 1.0


async def test_conversation_live_start_and_poll_to_completion(committed_session: AsyncSession) -> None:
    """A real customer message goes through the real multi-agent pipeline via the new HTTP API,
    from immediate 202 Accepted through to a finished, customer-safe status/response."""
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    await committed_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        start_response = await client.post(
            "/api/v1/conversations",
            json={"customer_id": str(customer.id), "message": "What is your refund policy?"},
            headers=auth_headers(customer.id),
        )
        print("\n--- LIVE CONVERSATION START RESPONSE ---")
        print(start_response.status_code, start_response.json())
        assert start_response.status_code == 202
        start_body = start_response.json()
        assert start_body["status"] == "in_progress"
        thread_id = start_body["thread_id"]

        loop = asyncio.get_running_loop()
        deadline = loop.time() + _POLL_TIMEOUT_SECONDS
        final_body: dict[str, object] = {}
        while loop.time() < deadline:
            status_response = await client.get(f"/api/v1/conversations/{thread_id}", headers=auth_headers(customer.id))
            assert status_response.status_code == 200
            final_body = status_response.json()
            print(f"--- POLL: status={final_body['status']} steps={final_body['steps']} ---")
            if final_body["status"] != "in_progress":
                break
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)

        print("--- LIVE CONVERSATION FINAL STATUS ---")
        print(final_body)
        assert final_body.get("status") in ("completed", "escalated", "awaiting_approval")
        assert final_body.get("final_response")
        assert final_body.get("steps")
