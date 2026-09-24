# app/core/middleware.py
# Purpose: Two small, focused Starlette middlewares added in Phase 10 (spec section 27):
#          - RequestIdMiddleware: generates/propagates a per-request id, stashes it in a
#            contextvar so every log line emitted while handling the request can include it (org
#            policy: "Every log: timestamp, request ID, operation, outcome"), and echoes it back
#            as an `X-Request-ID` response header for client-side correlation.
#          - SecurityHeadersMiddleware: adds baseline security response headers (spec section 27).
#            Deliberately minimal for this project's scope — a small, clearly-documented set, not
#            a full header-hardening framework.
# Author: CloudDesk Team
# Date: 2026-09-24

import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER: str = "X-Request-ID"

# Read by app.core.logging's formatter (via a logging.Filter) to attach the current request's id
# to every log record emitted during that request, without threading a request object through
# every function call in the codebase.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assign a request id (reusing an inbound `X-Request-ID` if the caller already set one, e.g.
    a load balancer/API gateway in front of this service) for the duration of one request."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


# Security headers (spec section 27). CSP is intentionally not applied here: this API serves JSON
# to a separate frontend origin, not HTML, so a browser CSP has no meaningful page to protect;
# the frontend's own Next.js response headers are the right place for that (see
# clouddesk/frontend/next.config.ts). HSTS is a documented deployment note, not set here, since it
# is only correct once TLS actually terminates in front of this service (see README's Production
# Deployment section) — sending it over plain HTTP in local dev would be actively wrong.
_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add baseline security response headers to every response."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        for name, value in _SECURITY_HEADERS.items():
            response.headers[name] = value
        return response
