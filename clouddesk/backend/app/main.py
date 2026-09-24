# app/main.py
# Purpose: FastAPI application entrypoint — wires up logging, CORS (Phase 9, spec section 25: the
#          Next.js frontend calls this API from a different origin), the v1 API router, and
#          translates service-layer exceptions into structured HTTP error responses.
# Author: CloudDesk Team
# Date: 2026-09-24

import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.exceptions import InvalidStateError, NotFoundError

configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
