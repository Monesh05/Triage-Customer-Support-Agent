# tests/test_api_conversations.py
# Purpose: Integration tests for the Phase 9 customer-facing chat API (spec section 25):
#          POST /api/v1/conversations returns 202 immediately without waiting on the (mocked)
#          multi-agent workflow, GET .../{thread_id} reflects progressive/final status derived
#          from real Phase 7 AgentRun trace rows, and an unknown thread_id 404s. The real
#          `run_support_workflow` is monkeypatched at its `app.services.conversation_service`
#          import site (never invoked directly) so these tests are fast and make no real LLM
#          calls — same mocking discipline as every other phase's API test suite. The one real
#          end-to-end run lives in tests/test_conversation_live_integration.py, marked
#          `integration` and excluded from the default run.
# Author: CloudDesk Team
# Date: 2026-09-24

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AgentRunStatus
from app.services import conversation_service, observability_service
from tests.conftest import new_id

_START = datetime(2026, 9, 24, 12, 0, 0, tzinfo=timezone.utc)
_POLL_TIMEOUT_SECONDS = 5.0
_POLL_INTERVAL_SECONDS = 0.02


async def _record_agent_run(session: AsyncSession, thread_id: str, agent_name: str, offset: int) -> None:
    start = _START + timedelta(seconds=offset)
    await observability_service.create_agent_run(
        session,
        ticket_id=None,
        thread_id=thread_id,
        agent_name=agent_name,
        start_time=start,
        end_time=start + timedelta(milliseconds=100),
        duration_ms=100,
        status=AgentRunStatus.SUCCESS,
        input_summary="hello",
        output_summary="ok",
        tool_calls=[],
        tool_results=[],
        error=None,
        iteration=None,
    )


def _make_fake_workflow(
    db_session: AsyncSession, *, delay_seconds: float, final_response: str = "All done!"
):
    """Build a fake `run_support_workflow` replacement: records a `triage` AgentRun, waits
    `delay_seconds`, records a `billing` AgentRun, then returns a completed SupportState-shaped
    dict. Mirrors the real workflow's observable side effect (progressive AgentRun rows) without
    any real LLM call.
    """

    async def _fake(
        customer_id: str,
        customer_message: str,
        conversation_history: list[str] | None = None,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        assert thread_id is not None
        await _record_agent_run(db_session, thread_id, "triage", 0)
        await asyncio.sleep(delay_seconds)
        await _record_agent_run(db_session, thread_id, "billing", 1)
        return {
            "ticket_id": None,
            "final_response": final_response,
            "human_approval_required": False,
            "escalation_required": False,
            "thread_id": thread_id,
        }

    return _fake


async def _poll_until(client: AsyncClient, thread_id: str, *, is_done) -> dict[str, Any]:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + _POLL_TIMEOUT_SECONDS
    while True:
        response = await client.get(f"/api/v1/conversations/{thread_id}")
        assert response.status_code == 200
        body = response.json()
        if is_done(body):
            return body
        if loop.time() > deadline:
            pytest.fail(f"Timed out waiting for conversation {thread_id}; last body: {body}")
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)


async def test_start_conversation_returns_202_immediately(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A short but nonzero delay: long enough that a response arriving with `status: in_progress`
    # proves the endpoint did NOT wait for the workflow to finish; short enough that the
    # background task has definitely completed (and stopped touching the shared test session)
    # before this test's fixtures tear down.
    monkeypatch.setattr(
        conversation_service, "run_support_workflow", _make_fake_workflow(db_session, delay_seconds=0.2)
    )

    response = await client.post(
        "/api/v1/conversations", json={"customer_id": str(uuid.uuid4()), "message": "I need help with my bill."}
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "in_progress"
    assert uuid.UUID(body["thread_id"])
    assert body["ticket_id"] is None

    # Drain the background task before teardown closes the shared db_session/connection.
    await _poll_until(client, body["thread_id"], is_done=lambda b: b["status"] != "in_progress")


async def test_poll_conversation_reflects_progressive_and_final_status(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        conversation_service,
        "run_support_workflow",
        _make_fake_workflow(db_session, delay_seconds=0.3, final_response="Your billing issue is resolved."),
    )

    start_response = await client.post(
        "/api/v1/conversations", json={"customer_id": str(uuid.uuid4()), "message": "Why was I charged twice?"}
    )
    thread_id = start_response.json()["thread_id"]

    # Mid-flight: the first (triage) step should already be "done" while the workflow is still
    # running (a synthetic trailing "in_progress" step stands in for it, per this endpoint's
    # design — see app.api.v1.conversations._build_steps).
    mid_flight = await _poll_until(
        client, thread_id, is_done=lambda body: any(s["step"] == "Understanding request" for s in body["steps"])
    )
    assert mid_flight["status"] == "in_progress"
    assert mid_flight["steps"][0] == {"step": "Understanding request", "status": "done"}
    assert mid_flight["steps"][-1]["status"] == "in_progress"
    assert mid_flight["final_response"] is None

    final_body = await _poll_until(client, thread_id, is_done=lambda body: body["status"] != "in_progress")
    assert final_body["status"] == "completed"
    assert final_body["final_response"] == "Your billing issue is resolved."
    assert [s["step"] for s in final_body["steps"]] == ["Understanding request", "Checking billing"]
    assert all(s["status"] == "done" for s in final_body["steps"])


async def test_poll_conversation_returns_404_for_unknown_thread_id(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/conversations/{new_id()}")

    assert response.status_code == 404


async def test_start_conversation_marks_failed_status_on_workflow_exception(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _fake_failure(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("simulated LLM outage")

    monkeypatch.setattr(conversation_service, "run_support_workflow", _fake_failure)

    start_response = await client.post(
        "/api/v1/conversations", json={"customer_id": str(uuid.uuid4()), "message": "Help!"}
    )
    thread_id = start_response.json()["thread_id"]

    final_body = await _poll_until(client, thread_id, is_done=lambda body: body["status"] != "in_progress")
    assert final_body["status"] == "failed"
    assert final_body["final_response"] == conversation_service.GENERIC_FAILURE_MESSAGE
