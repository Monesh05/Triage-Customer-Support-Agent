# Dockerfile
# Purpose: Container image for the CloudDesk FastAPI backend. Phase 10 (spec section 27)
#          hardening: multi-stage build (dependencies compiled/installed in a throwaway builder
#          stage so the final image carries no build toolchain), a non-root runtime user, and a
#          container-level HEALTHCHECK against the app's own /health endpoint.
# Author: CloudDesk Team
# Date: 2026-09-24

FROM python:3.13-slim AS builder

WORKDIR /app

# Install into a self-contained prefix so the runtime stage can copy just this, not pip/setuptools
# or any transitive build-time-only dependency.
COPY requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.13-slim AS runtime

# Non-root runtime user (spec section 27 production hardening): the app process never needs (and
# should never have) root inside the container.
RUN groupadd --system clouddesk && useradd --system --gid clouddesk --create-home clouddesk

WORKDIR /app

COPY --from=builder /install /usr/local
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

RUN chown -R clouddesk:clouddesk /app
USER clouddesk

EXPOSE 8000

# Liveness/readiness signal for orchestrators (docker compose, Kubernetes, Railway/Render/Fly.io —
# see the root README's Production Deployment section). Uses Python's stdlib rather than adding
# curl/wget to the image, keeping the runtime stage minimal.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
