# tests/test_observability_service.py
# Purpose: Unit tests for app.services.observability_service (Phase 7, spec section 24):
#          creating an AgentRun record, the redaction/truncation policy applied to
#          input/output summaries and tool calls/results, and querying a ticket's trace in
#          chronological order. Uses the real Postgres test database (same pattern as every
#          other service test in this suite) — no LLM calls involved.
# Author: CloudDesk Team
# Date: 2026-09-24

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AgentRunStatus, TicketPriority
from app.services import observability_service, ticket_service
from tests.factories import create_customer_with_account, create_org_and_plan

_START = datetime(2026, 9, 24, 12, 0, 0, tzinfo=timezone.utc)


async def _make_ticket(session: AsyncSession) -> uuid.UUID:
    org, _free, pro = await create_org_and_plan(session)
    customer = await create_customer_with_account(session, org, pro)
    ticket = await ticket_service.create_ticket(
        session, customer.id, "Test subject", "Test description",
        TicketPriority.MEDIUM, "test:actor",
    )
    return ticket.id


def test_truncate_bounds_length_and_marks_truncation() -> None:
    long_text = "a" * 1000
    result = observability_service.truncate(long_text, 50)

    assert len(result) == 50
    assert result.endswith(observability_service.TRUNCATION_MARKER)


def test_truncate_leaves_short_text_untouched() -> None:
    assert observability_service.truncate("short", 50) == "short"


def test_redact_mapping_replaces_sensitive_keys_recursively() -> None:
    data = {
        "customer_id": "cust-1",
        "api_key": "sk-live-abcdef123456",
        "nested": {"password": "hunter2", "amount": 49.0},
        "items": [{"token": "eyJhbGciOi..."}],
    }

    redacted = observability_service.redact_mapping(data)

    assert redacted["customer_id"] == "cust-1"
    assert redacted["api_key"] == observability_service.REDACTED_PLACEHOLDER
    assert redacted["nested"]["password"] == observability_service.REDACTED_PLACEHOLDER
    assert redacted["nested"]["amount"] == 49.0
    assert redacted["items"][0]["token"] == observability_service.REDACTED_PLACEHOLDER


def test_summarize_input_redacts_secrets_in_free_text() -> None:
    message = "My password: hunter2 and my card is 4111 1111 1111 1111, please help."

    summary = observability_service.summarize_input(message)

    assert summary is not None
    assert "hunter2" not in summary
    assert "4111" not in summary
    assert observability_service.REDACTED_PLACEHOLDER in summary


def test_summarize_input_truncates_long_messages() -> None:
    message = "please help " * 100  # well over INPUT_SUMMARY_MAX_LENGTH

    summary = observability_service.summarize_input(message)

    assert summary is not None
    assert len(summary) <= observability_service.INPUT_SUMMARY_MAX_LENGTH
    assert summary.endswith(observability_service.TRUNCATION_MARKER)


def test_summarize_input_none_for_empty_message() -> None:
    assert observability_service.summarize_input(None) is None
    assert observability_service.summarize_input("") is None


def test_summarize_output_redacts_and_truncates_structured_result() -> None:
    result = {
        "status": "resolved",
        "api_key": "sk-secret-value",
        "findings": ["x" * 500],
    }

    summary = observability_service.summarize_output(result)

    assert summary is not None
    assert "sk-secret-value" not in summary
    assert len(summary) <= observability_service.OUTPUT_SUMMARY_MAX_LENGTH


def test_summarize_tool_result_redacts_secret_fields() -> None:
    result = {"success": True, "data": {"token": "abc123", "amount": 10}}

    summarized = observability_service.summarize_tool_result(result)

    assert "abc123" not in str(summarized)


async def test_create_agent_run_persists_expected_fields(db_session: AsyncSession) -> None:
    ticket_id = await _make_ticket(db_session)
    end_time = _START + timedelta(milliseconds=850)

    agent_run = await observability_service.create_agent_run(
        db_session,
        ticket_id=ticket_id,
        thread_id="thread-1",
        agent_name="billing",
        start_time=_START,
        end_time=end_time,
        duration_ms=850,
        status=AgentRunStatus.SUCCESS,
        input_summary="Why was I charged twice?",
        output_summary='{"status": "resolved"}',
        tool_calls=[{"tool": "get_payment_history", "args": {}}],
        tool_results=[{"tool": "get_payment_history", "result": "ok"}],
        error=None,
        iteration=None,
    )

    assert agent_run.id is not None
    assert agent_run.ticket_id == ticket_id
    assert agent_run.agent_name == "billing"
    assert agent_run.status == AgentRunStatus.SUCCESS
    assert agent_run.duration_ms == 850
    assert agent_run.tool_calls == [{"tool": "get_payment_history", "args": {}}]


async def test_create_agent_run_truncates_overlong_error_message(db_session: AsyncSession) -> None:
    ticket_id = await _make_ticket(db_session)
    long_error = "boom " * 200

    agent_run = await observability_service.create_agent_run(
        db_session,
        ticket_id=ticket_id,
        thread_id="thread-err",
        agent_name="qa",
        start_time=_START,
        end_time=_START,
        duration_ms=5,
        status=AgentRunStatus.FAILURE,
        input_summary=None,
        output_summary=None,
        tool_calls=[],
        tool_results=[],
        error=long_error,
        iteration=1,
    )

    assert agent_run.error is not None
    assert len(agent_run.error) <= observability_service.ERROR_MESSAGE_MAX_LENGTH


async def test_get_trace_for_ticket_returns_chronological_order(db_session: AsyncSession) -> None:
    ticket_id = await _make_ticket(db_session)

    async def _record(agent_name: str, offset_seconds: int) -> None:
        start = _START + timedelta(seconds=offset_seconds)
        await observability_service.create_agent_run(
            db_session,
            ticket_id=ticket_id,
            thread_id="thread-order",
            agent_name=agent_name,
            start_time=start,
            end_time=start + timedelta(milliseconds=100),
            duration_ms=100,
            status=AgentRunStatus.SUCCESS,
            input_summary=None,
            output_summary=None,
            tool_calls=[],
            tool_results=[],
            error=None,
            iteration=None,
        )

    # Persisted out of chronological order on purpose.
    await _record("qa", 2)
    await _record("triage", 0)
    await _record("resolution", 1)

    trace = await observability_service.get_trace_for_ticket(db_session, ticket_id)

    assert [run.agent_name for run in trace] == ["triage", "resolution", "qa"]


async def test_get_agent_run_not_found_raises(db_session: AsyncSession) -> None:
    from app.services.exceptions import NotFoundError

    try:
        await observability_service.get_agent_run(db_session, uuid.uuid4())
        assert False, "expected NotFoundError"
    except NotFoundError:
        pass
