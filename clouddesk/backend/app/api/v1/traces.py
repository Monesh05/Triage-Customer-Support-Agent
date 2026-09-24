# app/api/v1/traces.py
# Purpose: Read-only REST endpoints for the Phase 7 Agent Observability trace records (spec
#          sections 24, 26). Returns the same redacted/truncated data already persisted by
#          app.services.observability_service — no additional business logic here. Phase 10
#          (spec section 27): internal-only, staff-role required — an agent execution trace is
#          exactly the "private chain-of-thought" detail a customer must never see directly (the
#          customer-facing view is the deliberately-redacted app.api.v1.conversations instead).
# Author: CloudDesk Team
# Date: 2026-09-24

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_staff_role
from app.database.session import get_db_session
from app.schemas.observability import AgentRunResponse, TicketTraceResponse
from app.services import observability_service
from app.services.ticket_service import get_ticket_by_id

router = APIRouter(tags=["observability"], dependencies=[Depends(require_staff_role)])


@router.get("/tickets/{ticket_id}/trace", response_model=TicketTraceResponse)
async def read_ticket_trace(
    ticket_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)
) -> TicketTraceResponse:
    """The ordered agent-execution trace for one ticket (spec section 24/26's Agent Trace view).

    Raises a 404 (via the app-wide `NotFoundError` handler) if the ticket itself does not exist;
    an existing ticket with no runs yet simply returns an empty `runs` list.
    """
    await get_ticket_by_id(session, ticket_id)  # 404s if the ticket does not exist.
    agent_runs = await observability_service.get_trace_for_ticket(session, ticket_id)
    return TicketTraceResponse(
        ticket_id=ticket_id, runs=[AgentRunResponse.from_agent_run(run) for run in agent_runs]
    )


@router.get("/traces/{run_id}", response_model=AgentRunResponse)
async def read_agent_run(
    run_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)
) -> AgentRunResponse:
    """A single agent-execution record by its `run_id`. 404s (via the app-wide `NotFoundError`
    handler) if no such run exists."""
    agent_run = await observability_service.get_agent_run(session, run_id)
    return AgentRunResponse.from_agent_run(agent_run)
