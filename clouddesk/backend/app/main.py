# app/main.py
# Purpose: FastAPI application entrypoint — wires up logging, CORS (Phase 9, spec section 25: the
#          Next.js frontend calls this API from a different origin), the v1 API router, and
#          translates service-layer exceptions into structured HTTP error responses. Phase 10
#          (spec section 27) additionally wires the request-id/security-headers middleware, the
#          slowapi rate limiter, and its 429 exception handler. The 2026-09-25 production-
#          hardening follow-up adds an application lifespan that warms up the Postgres-backed
#          LangGraph checkpointer's connection pool (and runs its one-time/idempotent schema
#          setup) once at startup rather than lazily on the first request, and closes that pool
#          cleanly on shutdown (see app.graph.graph.get_checkpointer/close_checkpointer).
# Author: CloudDesk Team
# Date: 2026-09-25

import asyncio
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

# `psycopg` (used by the Postgres-backed LangGraph checkpointer, see the lifespan below) refuses
# to run in async mode on Windows' default ProactorEventLoop - it needs a selector-based loop.
# This must be set before uvicorn creates its event loop, i.e. before anything below does
# asyncio.run()/get_event_loop() as a side effect of import - hence right at the top of this
# module, which uvicorn imports before starting its loop. Matches tests/conftest.py's identical
# fix for the same constraint under pytest-asyncio.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import limiter
from app.graph.graph import close_checkpointer, get_checkpointer
from app.services.exceptions import InvalidStateError, NotFoundError

configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Warm up the checkpointer's connection pool (and its idempotent schema setup) once at
    startup, so the first real request never pays that cost, and close the pool cleanly on
    shutdown rather than leaking connections when the process exits.
    """
    try:
        await get_checkpointer()
    except Exception:
        logger.exception("checkpointer_startup_failed")
        raise
    try:
        yield
    finally:
        await close_checkpointer()


app = FastAPI(title=settings.app_name, lifespan=_lifespan)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Translate a slowapi rate-limit breach into a 429 with a safe, generic message."""
    logger.warning("rate_limit_exceeded path=%s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Too many requests. Please try again later."},
    )


# Middleware executes in reverse-registration order for the request path, so registering
# RequestIdMiddleware last ensures its context is established before CORS/security-header
# middleware (and every route handler) runs, while its response header is still applied on the
# way out.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    """Translate a missing-resource service error into a 404 response."""
    logger.warning("Not found on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})


@app.exception_handler(InvalidStateError)
async def invalid_state_handler(request: Request, exc: InvalidStateError) -> JSONResponse:
    """Translate an invalid-state service error into a 409 Conflict response."""
    logger.warning("Invalid state on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Simple liveness probe."""
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.api_v1_prefix)
