# tests/conftest.py
# Purpose: Shared pytest fixtures for the CloudDesk backend test suite. Tests run against a
#          real PostgreSQL database (a dedicated `clouddesk_test` database alongside the dev
#          `clouddesk` database) rather than sqlite, because the schema uses Postgres-only
#          features (native ENUM types, JSONB columns) that sqlite cannot represent.
#
#          Schema creation runs once, synchronously, in `pytest_sessionstart` using its own
#          throwaway event loop (via asyncio.run) — kept independent of pytest-asyncio's
#          per-test event loops, which avoids "attached to a different loop" errors from
#          asyncpg on Windows' Proactor event loop when a long-lived engine/connection is
#          reused across test-scoped loops. Each test then gets its own async engine bound to
#          its own event loop, with all changes rolled back afterwards for isolation.
# Author: CloudDesk Team
# Date: 2026-09-21

import asyncio
import os
import sys
import uuid
from collections.abc import AsyncGenerator

# Point the app at the test database BEFORE any `app.*` module is imported, since
# app.core.config.get_settings() is cached on first call.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://clouddesk:clouddesk@localhost:5433/clouddesk_test",
)

# The 2026-09-25 production-hardening fix's Postgres checkpointer uses `psycopg` (v3) in async
# mode, which refuses to run on Windows' default `ProactorEventLoop` (it needs a selector-based
# loop for its socket waiter). `uvicorn` already sets this same policy in real deployments
# (uvicorn/loops/asyncio.py) since it has no `uvloop` build for Windows; pytest-asyncio does not,
# so it must be set explicitly here, before any test creates an event loop. Harmless for
# asyncpg/SQLAlchemy (neither requires Proactor-only features such as subprocess pipes).
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings
from app.core.security import AuthRole, create_access_token
from app.database.base import Base
from app.database.session import get_db_session
from app.main import app
from app.models import (  # noqa: F401  (register all models on Base.metadata)
    Account,
    AgentRun,
    ApiKey,
    AuditLog,
    Customer,
    Entitlement,
    Invoice,
    KnowledgeChunk,
    KnowledgeDocument,
    Organization,
    Payment,
    Plan,
    RefundRequest,
    ServiceIncident,
    StaffUser,
    Subscription,
    SupportPolicy,
    SupportTicket,
    UsageRecord,
)


async def _create_schema() -> None:
    """Create the test schema fresh, including the `vector` extension Phase 6's
    KnowledgeChunk.embedding column (pgvector) requires."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


def pytest_sessionstart(session: pytest.Session) -> None:  # noqa: ARG001
    """Create (fresh) all tables in the test database once, before any test runs."""
    asyncio.run(_create_schema())


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session bound to a rolled-back-per-test transaction for isolation.

    A dedicated engine is created per test (bound to that test's own event loop) and
    disposed at teardown, since asyncpg connections cannot cross event loops.
    """
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(bind=connection, expire_on_commit=False)
            try:
                yield session
            finally:
                await session.close()
                await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """An httpx AsyncClient wired to the FastAPI app, using the isolated test session."""

    async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
async def _reset_checkpointer_pool() -> AsyncGenerator[None, None]:
    """Close the LangGraph Postgres checkpointer's connection pool after every test.

    Each test function runs in its own event loop (see this module's docstring on `db_session`
    for the same asyncpg constraint); a `psycopg` connection pool opened during one test's loop
    cannot be reused once that loop is closed. `app.graph.graph.get_checkpointer()` lazily
    recreates the pool (and re-runs its cheap, idempotent `.setup()`) on next use, so tests never
    share a pool across event loops.
    """
    from app.graph.graph import close_checkpointer

    yield
    await close_checkpointer()


@pytest.fixture(autouse=True)
async def _reset_shared_engine_pool() -> AsyncGenerator[None, None]:
    """Dispose the app's shared asyncpg engine pool (app.database.engine.engine) around every
    test, not only the ones using the `committed_session` fixture.

    Before the 2026-09-25 persistence fix, `app.services.conversation_service` never touched
    `get_session()` (a pure in-memory dict), so tests/test_api_conversations.py never exercised
    this pool at all despite running many test functions (each its own event loop) back to back.
    Now that conversation-record reads/writes go through `get_session()`, those tests hit the
    exact same cross-event-loop asyncpg hazard `committed_session`'s docstring already describes
    (a pooled connection bound to one test's now-closed event loop cannot be reused by the next
    test's loop) — so the same disposal `committed_session` already did for its own tests is now
    needed unconditionally.
    """
    from app.database.engine import engine
    from app.services.conversation_service import drain_background_tasks

    await engine.dispose()
    yield
    # Drain any conversation background task still in flight BEFORE disposing the pool (and
    # before this test's event loop closes) - otherwise its DB session survives into a later
    # test's loop and fails with "attached to a different loop" once garbage-collected there.
    await drain_background_tasks()
    await engine.dispose()


def new_id() -> uuid.UUID:
    """Convenience helper for generating a random id in tests (e.g. a not-found lookup)."""
    return uuid.uuid4()


def auth_headers(customer_id: uuid.UUID) -> dict[str, str]:
    """A valid `Authorization` header for the given customer id (Phase 10, spec section 27).

    Issues a real, signed access token directly via app.core.security rather than going through
    POST /api/v1/auth/login — tests exercising the login endpoint itself live in
    test_api_auth.py; every other protected-endpoint test only needs a valid token for a customer
    it already created, which this avoids a redundant extra HTTP round-trip for.
    """
    token = create_access_token(AuthRole.CUSTOMER, subject=str(customer_id), customer_id=customer_id)
    return {"Authorization": f"Bearer {token}"}


def staff_auth_headers(staff_id: uuid.UUID | None = None) -> dict[str, str]:
    """A valid `Authorization` header for a staff (internal support-console) token."""
    token = create_access_token(AuthRole.STAFF, subject=str(staff_id or uuid.uuid4()))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def staff_user(db_session: AsyncSession) -> StaffUser:
    """A staff account visible to the same rolled-back-per-test session the `client` fixture
    uses, for tests that exercise POST /api/v1/auth/staff/login itself (which looks the account
    up by email/password, unlike `staff_auth_headers` above)."""
    from app.core.security import hash_password

    staff = StaffUser(
        name="Test Staff", email=f"staff-{uuid.uuid4()}@clouddesk.example", password_hash=hash_password("staff1234")
    )
    db_session.add(staff)
    await db_session.flush()
    return staff


@pytest.fixture
async def committed_session() -> AsyncGenerator[AsyncSession, None]:
    """A session bound to the app's real engine (app.database.engine.AsyncSessionFactory),
    NOT a rolled-back-per-test transaction.

    The Phase 2 tool layer (app.tools.*) opens its own session via
    app.database.session.get_session(), on a separate DB connection from the `db_session`
    fixture. Because Postgres connections don't see each other's uncommitted rows, tool
    tests must commit real data through this fixture rather than `db_session`. Any
    Organization created by the test is deleted (cascading to its customers/accounts/
    subscriptions/etc. via ON DELETE CASCADE) during teardown to avoid leaking rows across
    the test session.

    The module-level `engine`/`AsyncSessionFactory` in app.database.engine are created once
    at import time, but pytest-asyncio gives each test its own event loop, and asyncpg
    connections cannot cross event loops (same constraint `db_session` works around with a
    per-test engine). Disposing the shared engine's pool before and after the test forces
    both this fixture's session AND any session app.tools.* opens via get_session() to open
    fresh connections bound to the CURRENT test's loop.
    """
    from sqlalchemy import delete as sa_delete

    from app.database.engine import AsyncSessionFactory, engine
    from app.models.organization import Organization

    await engine.dispose()
    created_org_ids: list[uuid.UUID] = []
    try:
        async with AsyncSessionFactory() as session:
            session.info["created_org_ids"] = created_org_ids
            try:
                yield session
            finally:
                for org_id in created_org_ids:
                    await session.execute(sa_delete(Organization).where(Organization.id == org_id))
                await session.commit()
    finally:
        await engine.dispose()
