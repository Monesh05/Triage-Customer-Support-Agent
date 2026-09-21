# app/database/session.py
# Purpose: FastAPI dependency that yields a scoped async SQLAlchemy session per request,
#          ensuring rollback-on-error and proper cleanup. Also provides `get_session()`, an
#          async context manager for obtaining a session OUTSIDE of FastAPI's DI system —
#          used by the Phase 2 tool layer (app/tools/*), which runs as plain async functions
#          rather than request handlers.
# Author: CloudDesk Team
# Date: 2026-09-21

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.engine import AsyncSessionFactory

logger = logging.getLogger(__name__)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session, rolling back on error and always closing it."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            logger.exception("Database session error; rolling back transaction.")
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager yielding a DB session for callers outside a FastAPI request.

    Usage: `async with get_session() as session: ...`. Rolls back on error and always
    closes the session, mirroring `get_db_session` but usable from tools/scripts.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            logger.exception("Database session error; rolling back transaction.")
            await session.rollback()
            raise
        finally:
            await session.close()
