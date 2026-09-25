# app/graph/graph.py
# Purpose: Assembles and compiles the support StateGraph (spec sections 3, 18-22):
#          START -> triage -> [parallel specialist fan-out OR straight to escalation]
#                -> resolution -> qa -> [back to resolution | escalation | finalize] -> END,
#          with finalize -> await_human_decision -> END added in Phase 5 whenever human approval
#          is required. The graph is compiled WITH a checkpointer (spec section 22: "use LangGraph
#          interruption/checkpoint mechanisms") so `await_human_decision_node`'s `interrupt()`
#          call actually pauses a run rather than merely reporting "approval needed" after fully
#          finishing. `run_support_workflow` starts a new run (and pending actions arising from it
#          are persisted via app.services.approval_service, and a `support_tickets` row is
#          best-effort auto-created up front per Phase 7 — see `_create_ticket_if_possible` —
#          since a trace with no ticket to hang off of is much less useful, spec sections 7/26);
#          `resume_support_workflow` continues a previously paused run once a human decision has
#          been recorded for every one of its pending actions.
#
#          Production-hardening follow-up (2026-09-25, closes a gap flagged in the Phase 5 and
#          Phase 9 reports and in README's "Production Deployment" section): the checkpointer is
#          now `langgraph-checkpoint-postgres`'s `AsyncPostgresSaver`, backed by the SAME Postgres
#          database this app already uses (`DATABASE_URL`, via `get_settings()`) rather than the
#          Phase 5-era in-process `MemorySaver`. A paused-awaiting-approval or in-flight thread's
#          state now survives a full backend process restart — see `get_checkpointer` and
#          `close_checkpointer` below for the connection-pool lifecycle, and app.main's lifespan
#          for where those are actually called.
# Author: CloudDesk Team
# Date: 2026-09-25

import asyncio
import logging
import uuid
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.core.config import get_settings
from app.database.session import get_session
from app.graph import nodes, resolution_nodes
from app.graph.routing import route_after_finalize, route_after_qa, route_after_triage
from app.graph.state import SupportState, build_initial_state
from app.models.enums import TicketPriority
from app.services import approval_service, ticket_service
from app.services.exceptions import InvalidStateError

logger = logging.getLogger("clouddesk.graph")

TICKET_SUBJECT_MAX_LENGTH: int = 117  # Column is String(255); leaves room for an added "...".
WORKFLOW_TICKET_ACTOR: str = "system:support_workflow"

SPECIALIST_NODES: tuple[str, ...] = ("billing", "account", "technical", "product")

# The checkpointer's own connection pool, sized independently of SQLAlchemy's asyncpg pool (they
# are two different drivers/pools against the same database — see module docstring). A support
# workflow run is a single sequential chain of node executions per thread, never many concurrent
# checkpoint writes for the same run, so a small pool comfortably covers many concurrent
# *different* customers' conversations.
CHECKPOINTER_POOL_MAX_SIZE: int = 10

# How long a checkpointer connection may sit idle in the pool before it is proactively closed and
# reopened, rather than risk it being one a suspend-on-idle provider (e.g. Neon's free tier) has
# already terminated server-side. Comfortably under typical free-tier auto-suspend windows.
CHECKPOINTER_POOL_MAX_IDLE_SECONDS: float = 120.0

_checkpointer: AsyncPostgresSaver | None = None
_checkpointer_pool: AsyncConnectionPool | None = None
# Created lazily (never at module import time) and reset alongside the checkpointer in
# close_checkpointer(): an asyncio.Lock is bound to whichever event loop first awaits it, and
# pytest-asyncio gives each test its own event loop (see tests/conftest.py), so a lock created
# once at import time would hang forever on its second test - the same constraint already
# documented for the SQLAlchemy engine and this module's connection pool.
_checkpointer_init_lock: asyncio.Lock | None = None


def _get_init_lock() -> asyncio.Lock:
    global _checkpointer_init_lock
    if _checkpointer_init_lock is None:
        _checkpointer_init_lock = asyncio.Lock()
    return _checkpointer_init_lock


def _psycopg_conn_string(database_url: str) -> str:
    """Adapt the app's SQLAlchemy connection URL (`postgresql+asyncpg://...`) into the plain
    libpq connection string `psycopg` (the driver `langgraph-checkpoint-postgres` uses — not
    `asyncpg`) expects. Same host/port/database/credentials; only the URL scheme differs, PLUS
    one query-parameter-naming difference: SQLAlchemy's asyncpg dialect forwards URL query
    params as literal Python kwargs to `asyncpg.connect()`, which has an `ssl` parameter (not
    `sslmode`) - so `DATABASE_URL` uses `?ssl=require` for managed providers like Neon that
    require TLS. `psycopg`/libpq instead expects the standard `sslmode` parameter name and
    rejects a bare `ssl` query parameter outright - so that one key needs translating here.
    """
    parsed = urlsplit(database_url.replace("postgresql+asyncpg://", "postgresql://", 1))
    query_params = parse_qsl(parsed.query, keep_blank_values=True)
    translated = [("sslmode" if key == "ssl" else key, value) for key, value in query_params]
    return urlunsplit(parsed._replace(query=urlencode(translated)))


async def get_checkpointer() -> AsyncPostgresSaver:
    """Return the process-wide Postgres-backed checkpointer, creating its connection pool and
    running its idempotent schema setup on first use.

    `AsyncPostgresSaver.setup()` creates (or upgrades) the checkpointer's own tables
    (`checkpoints`, `checkpoint_writes`, `checkpoint_blobs`) and tracks its own migration version
    in a `checkpoint_migrations` table it manages entirely itself — it is explicitly documented as
    safe/idempotent to call every time (it no-ops once already at the latest version), which is
    why this is called here at startup rather than folded into an Alembic migration: Alembic would
    have no way to know about (and would conflict with) that library-internal version tracking the
    next time a new `langgraph-checkpoint-postgres` release adds a migration of its own.
    """
    global _checkpointer, _checkpointer_pool
    async with _get_init_lock():
        if _checkpointer is not None:
            return _checkpointer
        conn_string = _psycopg_conn_string(get_settings().database_url)
        # `autocommit=True` matches what AsyncPostgresSaver.from_conn_string uses (and is
        # required: its own schema-setup migrations run `CREATE INDEX CONCURRENTLY`, which
        # Postgres refuses inside a multi-statement transaction block). `row_factory=dict_row` and
        # `prepare_threshold=0` likewise match that reference implementation's connection setup.
        #
        # `check=AsyncConnectionPool.check_connection` and a short `max_idle` (found live in
        # production, 2026-09-25): a managed Postgres provider that auto-suspends on idle (e.g.
        # Neon's free tier) unilaterally closes connections the pool still believes are healthy,
        # which surfaced as `psycopg.errors.AdminShutdown` on every single conversation - the pool
        # kept handing out connections the server had already killed. `check_connection` pings a
        # connection with a cheap query before handing it to a caller and transparently discards
        # and replaces it if that fails; `max_idle` proactively recycles connections that have sat
        # unused long enough to be a suspend/AdminShutdown risk, rather than waiting to discover
        # they are dead on the next request.
        pool = AsyncConnectionPool(
            conn_string,
            open=False,
            max_size=CHECKPOINTER_POOL_MAX_SIZE,
            max_idle=CHECKPOINTER_POOL_MAX_IDLE_SECONDS,
            check=AsyncConnectionPool.check_connection,
            kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": 0},
        )
        try:
            await pool.open(wait=True)
            checkpointer = AsyncPostgresSaver(conn=pool)
            await checkpointer.setup()
        except Exception:
            logger.exception("checkpointer_setup_failed")
            await pool.close()
            raise
        _checkpointer_pool = pool
        _checkpointer = checkpointer
        logger.info("checkpointer_ready backend=postgres pool_max_size=%d", CHECKPOINTER_POOL_MAX_SIZE)
        return _checkpointer


async def close_checkpointer() -> None:
    """Close the checkpointer's connection pool and drop the cached compiled graph.

    Called from app.main's FastAPI lifespan on shutdown, and from the test suite's per-test
    teardown (tests/conftest.py): psycopg connections, like asyncpg's, cannot be reused across the
    function-scoped event loop pytest-asyncio gives each test (see tests/conftest.py's module
    docstring for the same constraint already documented there for the SQLAlchemy engine), so
    tests close and recreate this pool once per test rather than sharing one across event loops.
    """
    global _checkpointer, _checkpointer_pool, _compiled_graph, _checkpointer_init_lock
    if _checkpointer_pool is not None:
        try:
            await _checkpointer_pool.close()
        except Exception:
            logger.exception("checkpointer_pool_close_failed")
    _checkpointer = None
    _checkpointer_pool = None
    _compiled_graph = None
    _checkpointer_init_lock = None


def _register_nodes(graph: StateGraph[SupportState]) -> None:
    graph.add_node("triage", nodes.triage_node)
    graph.add_node("billing", nodes.billing_node)
    graph.add_node("account", nodes.account_node)
    graph.add_node("technical", nodes.technical_node)
    graph.add_node("product", nodes.product_node)
    graph.add_node("resolution", resolution_nodes.resolution_node)
    graph.add_node("qa", resolution_nodes.qa_node)
    graph.add_node("escalation", resolution_nodes.escalation_node)
    graph.add_node("finalize", resolution_nodes.finalize_node)
    graph.add_node("await_human_decision", resolution_nodes.await_human_decision_node)


def _wire_edges(graph: StateGraph[SupportState]) -> None:
    graph.add_edge(START, "triage")

    # Dynamic router (spec section 20): fans out into 1-4 specialist nodes running in parallel,
    # or routes straight to escalation on an explicit human request / unrecognized intent.
    # Whichever specialists run all converge on "resolution" (automatic fan-in).
    triage_path_map = {name: name for name in (*SPECIALIST_NODES, "escalation")}
    graph.add_conditional_edges("triage", route_after_triage, triage_path_map)
    for specialist in SPECIALIST_NODES:
        graph.add_edge(specialist, "resolution")
    graph.add_edge("resolution", "qa")

    # Reflection loop (spec section 21): bounded return to "resolution" before escalation.
    graph.add_conditional_edges(
        "qa", route_after_qa, {"resolution": "resolution", "escalation": "escalation", "finalize": "finalize"}
    )

    # Human-in-the-loop (spec section 22): finalize only decides whether approval is required;
    # the pause itself happens in await_human_decision (see that node's docstring for why).
    graph.add_conditional_edges(
        "finalize", route_after_finalize, {"await_human_decision": "await_human_decision", "end": END}
    )
    graph.add_edge("escalation", END)
    graph.add_edge("await_human_decision", END)


def build_support_graph(checkpointer: AsyncPostgresSaver) -> CompiledStateGraph:
    """Build and compile the support StateGraph. See module docstring for the topology."""
    graph: StateGraph[SupportState] = StateGraph(SupportState)
    _register_nodes(graph)
    _wire_edges(graph)
    return graph.compile(checkpointer=checkpointer)


_compiled_graph: CompiledStateGraph | None = None


async def get_support_graph() -> CompiledStateGraph:
    """Return the compiled support graph, building it once (against the process-wide Postgres
    checkpointer, see `get_checkpointer`) and reusing it thereafter.

    Async (unlike its Phase 5-9 predecessor) because obtaining the checkpointer requires an async
    connection-pool setup on first use. Every caller of this function is already inside an `async
    def` (the graph itself runs entirely through `ainvoke`/`aget_state`), so this is not a
    breaking change for any real call site — only test code that called it synchronously needed
    an `await` added.
    """
    global _compiled_graph
    if _compiled_graph is None:
        checkpointer = await get_checkpointer()
        _compiled_graph = build_support_graph(checkpointer)
    return _compiled_graph


def _thread_config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


async def _persist_pending_actions(customer_id: str, thread_id: str, state: SupportState) -> None:
    """Create one persistent ApprovalRequest row (app.services.approval_service) per pending
    action a paused run just surfaced, so the approval API/UI has something to list and decide on.
    """
    pending_actions = state.get("pending_actions", [])
    if not pending_actions:
        return
    try:
        customer_uuid = uuid.UUID(customer_id)
    except ValueError:
        # customer_id isn't a real customer record id (e.g. a mocked-agent test double) — the
        # paused state is still returned to the caller with human_approval_required/pending_actions
        # set; only the persistent approval-queue bookkeeping is skipped, same as any other
        # non-fatal side effect in this workflow (spec section 27: never crash on a side channel).
        logger.warning("skip_persist_pending_actions reason=invalid_customer_id thread_id=%s", thread_id)
        return

    async with get_session() as session:
        for action in pending_actions:
            agent_name = str(action.get("agent", "unknown"))
            await approval_service.create_pending_action(
                session, customer_uuid, thread_id, agent_name, action
            )


def _derive_ticket_subject(customer_message: str) -> str:
    """A short ticket subject line from the raw customer message (spec section 5's `subject`
    is a required, length-bounded field; the full message is kept verbatim as `description`)."""
    stripped = customer_message.strip() or "Support request"
    if len(stripped) <= TICKET_SUBJECT_MAX_LENGTH:
        return stripped
    return stripped[:TICKET_SUBJECT_MAX_LENGTH].rstrip() + "..."


async def _create_ticket_if_possible(customer_id: str, customer_message: str) -> str | None:
    """Best-effort auto-create a `SupportTicket` for this workflow run (Phase 7, spec sections
    7/24/26: tickets are the top-level object a trace hangs off of, and none was ever created for
    a support-workflow run before this phase). Mirrors `_persist_pending_actions`'s non-fatal
    handling of a non-UUID/unknown customer id: this bookkeeping must never block or crash the
    actual support workflow, so any failure here just means `ticket_id` stays `None`.
    """
    try:
        customer_uuid = uuid.UUID(customer_id)
    except ValueError:
        logger.warning("skip_ticket_autocreate reason=invalid_customer_id")
        return None
    try:
        async with get_session() as session:
            ticket = await ticket_service.create_ticket(
                session,
                customer_uuid,
                subject=_derive_ticket_subject(customer_message),
                description=customer_message,
                priority=TicketPriority.MEDIUM,
                actor=WORKFLOW_TICKET_ACTOR,
            )
            return str(ticket.id)
    except Exception:  # noqa: BLE001 - see docstring: never block the workflow on this
        logger.exception("ticket_autocreate_failed customer_id=%s", customer_id)
        return None


async def run_support_workflow(
    customer_id: str,
    customer_message: str,
    conversation_history: list[str] | None = None,
    thread_id: str | None = None,
) -> SupportState:
    """Build the initial state and run the support workflow, returning the final (or paused)
    state. When the run pauses for human approval, `final_state["human_approval_required"]` is
    True, `final_state["thread_id"]` identifies the paused run, and a persistent approval-queue
    row has already been created for each pending action (spec section 22).

    `thread_id` (Phase 9, spec section 25) lets a caller pre-generate the LangGraph thread id
    BEFORE this (potentially 20-100s) coroutine starts, so an async API layer can register a
    pollable conversation record and hand the id back to the caller immediately, instead of
    waiting for the whole run to know it. Omitted (the default), behavior is unchanged from
    every existing caller: a fresh id is generated by `build_initial_state`.
    """
    logger.info("support_workflow_start customer_id=%s", customer_id)
    ticket_id = await _create_ticket_if_possible(customer_id, customer_message)
    initial_state = build_initial_state(
        customer_id, customer_message, conversation_history, thread_id=thread_id, ticket_id=ticket_id
    )
    thread_id = initial_state["thread_id"]
    graph = await get_support_graph()
    final_state: SupportState = await graph.ainvoke(initial_state, config=_thread_config(thread_id))

    if final_state.get("human_approval_required") and final_state.get("pending_actions"):
        await _persist_pending_actions(customer_id, thread_id, final_state)

    logger.info(
        "support_workflow_end customer_id=%s thread_id=%s escalation_required=%s human_approval_required=%s",
        customer_id, thread_id, final_state.get("escalation_required"), final_state.get("human_approval_required"),
    )
    return final_state


async def resume_support_workflow(thread_id: str, decision: dict[str, Any]) -> SupportState:
    """Resume a previously paused run once a human decision is available for its pending actions.

    `decision` is `{"actions": [{"action_id": str, "status": "approved"|"rejected", ...}, ...]}`,
    matching every entry the paused state's `pending_actions` produced (see
    app.graph.resolution_nodes.await_human_decision_node).

    Raises:
        InvalidStateError: if `thread_id` has no run currently paused waiting on a decision.
    """
    graph = await get_support_graph()
    config = _thread_config(thread_id)

    snapshot = await graph.aget_state(config)
    if not snapshot or not snapshot.next:
        raise InvalidStateError(f"No paused workflow run found for thread {thread_id}")

    logger.info("support_workflow_resume thread_id=%s", thread_id)
    final_state: SupportState = await graph.ainvoke(Command(resume=decision), config=config)
    logger.info(
        "support_workflow_resumed thread_id=%s final_response_set=%s",
        thread_id, bool(final_state.get("final_response")),
    )
    return final_state
