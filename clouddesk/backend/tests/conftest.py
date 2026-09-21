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
import uuid
from collections.abc import AsyncGenerator

# Point the app at the test database BEFORE any `app.*` module is imported, since
# app.core.config.get_settings() is cached on first call.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://clouddesk:clouddesk@localhost:5433/clouddesk_test",
)

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings
from app.database.base import Base
from app.database.session import get_db_session
from app.main import app
from app.models import (  # noqa: F401  (register all models on Base.metadata)
    Account,
    ApiKey,
    AuditLog,
    Customer,
    Entitlement,
    Invoice,
    Organization,
    Payment,
    Plan,
    RefundRequest,
    ServiceIncident,
    Subscription,
    SupportPolicy,
    SupportTicket,
    UsageRecord,
)


async def _create_schema() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    async with engine.begin() as conn:
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


def new_id() -> uuid.UUID:
    """Convenience helper for generating a random id in tests (e.g. a not-found lookup)."""
    return uuid.uuid4()
