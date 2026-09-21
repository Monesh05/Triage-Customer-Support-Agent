# app/database/session.py
# Purpose: FastAPI dependency that yields a scoped async SQLAlchemy session per request,
#          ensuring rollback-on-error and proper cleanup.
# Author: CloudDesk Team
# Date: 2026-09-21

import logging
from collections.abc import AsyncGenerator

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
