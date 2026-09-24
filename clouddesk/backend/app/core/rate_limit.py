# app/core/rate_limit.py
# Purpose: Shared slowapi Limiter instance (spec section 27) used by app.main (registration/
#          exception handler) and individual routers (`@limiter.limit(...)` decorators). A single
#          module-level instance avoids each router constructing its own and disagreeing on the
#          key function.
# Author: CloudDesk Team
# Date: 2026-09-24

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.security import TokenError, decode_access_token


def _rate_limit_key(request: Request) -> str:
    """Key the rate limit by authenticated identity when a valid bearer token is present, falling
    back to source IP for unauthenticated requests (e.g. login itself, where there is no identity
    yet — brute-force protection must key by IP there).
    """
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[len("bearer ") :].strip()
        try:
            claims = decode_access_token(token)
            return f"{claims.role.value}:{claims.subject}"
        except TokenError:
            pass  # Fall through to IP-based keying; the request will separately 401 downstream.
    return get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key)
