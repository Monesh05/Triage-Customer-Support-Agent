# CloudDesk

CloudDesk is a fictional B2B SaaS product used as the foundation for a multi-agent AI
customer-support platform. The full project vision (LangGraph multi-agent orchestration,
RAG, human-in-the-loop approvals, a customer portal, etc.) is described in
`CloudDesk_Multi_Agent_Project_Spec.md`.

**This repository currently implements Phase 1 only: the CloudDesk SaaS backend itself** —
a real FastAPI + PostgreSQL application with customers, organizations, subscriptions,
plans, payments, invoices, API keys, usage records, service incidents, and support
tickets. Later phases (tool layer, agents, LangGraph, RAG, frontend) are not implemented
yet.

## Project layout

```text
clouddesk/
├── backend/            # FastAPI application (Phase 1)
│   ├── app/
│   │   ├── api/v1/     # REST routers
│   │   ├── models/     # SQLAlchemy ORM models
│   │   ├── schemas/    # Pydantic v2 request/response schemas
│   │   ├── services/   # Business logic (routers call services, never the DB directly)
│   │   ├── database/   # Engine/session/declarative base
│   │   ├── core/       # Settings (pydantic-settings) and logging config
│   │   └── main.py     # FastAPI app entrypoint
│   ├── alembic/        # Database migrations
│   └── tests/          # pytest unit + integration tests
├── data/seed/          # Seed data script and fixtures
docker-compose.yml       # PostgreSQL (+ optional backend container) for local dev
.env.example
```

## Prerequisites

- Python 3.13
- Docker Desktop (for PostgreSQL)

## Running Phase 1 locally

1. **Start PostgreSQL:**

   ```bash
   docker compose up -d postgres
   ```

   This starts Postgres on host port `5433` (container port `5432`), with database/user/
   password all `clouddesk`. It also creates a `clouddesk_test` database is NOT created
   automatically — see the Testing section below for the one-time command to create it.

2. **Set up the backend virtual environment and install dependencies:**

   ```bash
   cd clouddesk/backend
   python -m venv .venv
   ./.venv/Scripts/pip install -r requirements.txt      # Windows
   # source .venv/bin/activate && pip install -r requirements.txt   # macOS/Linux
   ```

3. **Configure environment variables:**

   Copy `.env.example` (repo root) into `clouddesk/backend/.env` and adjust if needed.
   The default `DATABASE_URL` already points at the docker-compose Postgres instance
   on `localhost:5433`.

4. **Run database migrations:**

   ```bash
   cd clouddesk/backend
   ./.venv/Scripts/python -m alembic upgrade head
   ```

5. **Seed the database with realistic Phase 1 data:**

   ```bash
   cd clouddesk           # run from clouddesk/, not clouddesk/backend/
   ../clouddesk/backend/.venv/Scripts/python -m data.seed.seed
   # or, with DATABASE_URL exported explicitly:
   # DATABASE_URL=postgresql+asyncpg://clouddesk:clouddesk@localhost:5433/clouddesk \
   #   ./backend/.venv/Scripts/python -m data.seed.seed
   ```

   This creates 5 organizations, 4 plans (Free/Pro/Business/Enterprise), 5 support
   policies, 4 service incidents, and 40 customers spanning: healthy accounts,
   duplicate-payment customers, failed/pending-payment customers, stale-entitlement
   customers (Pro subscription but a Free-level entitlement — the classic sync-lag bug),
   locked accounts, and false-positive "heavy but legitimate usage" customers. The
   script is idempotent-safe: it refuses to re-seed if organizations already exist.

6. **Run the API:**

   ```bash
   cd clouddesk/backend
   ./.venv/Scripts/python -m uvicorn app.main:app --reload
   ```

   Then try, e.g.:

   ```bash
   curl http://127.0.0.1:8000/health
   curl http://127.0.0.1:8000/api/v1/incidents
   ```

   Interactive API docs are available at `http://127.0.0.1:8000/docs`.

### Docker Compose (backend + Postgres together)

`docker-compose.yml` also defines a `backend` service that builds
`clouddesk/backend/Dockerfile` and runs uvicorn. Bring both up with:

```bash
docker compose up -d --build
```

(Run migrations/seed manually inside or against the container as in steps 4–5 above.)

## Testing

Tests run against a **real PostgreSQL database** (a separate `clouddesk_test` database),
not sqlite, because the schema uses Postgres-only features (native `ENUM` types, `JSONB`
columns) that sqlite cannot represent faithfully. Create the test database once:

```bash
docker exec clouddesk-postgres psql -U clouddesk -d clouddesk -c "CREATE DATABASE clouddesk_test OWNER clouddesk;"
```

Then run the suite:

```bash
cd clouddesk/backend
./.venv/Scripts/python -m pytest -q
```

`tests/conftest.py` creates all tables once at session start and rolls back each test's
changes in an isolated transaction, so tests do not interfere with each other or with the
`clouddesk` development database.

## API endpoints (Phase 1)

```text
GET    /api/v1/customers/{customer_id}
GET    /api/v1/accounts/{customer_id}
GET    /api/v1/subscriptions/{customer_id}
GET    /api/v1/payments/{customer_id}
GET    /api/v1/invoices/{customer_id}
GET    /api/v1/usage/{customer_id}
GET    /api/v1/api-keys/{customer_id}      # never returns raw keys or key_hash
GET    /api/v1/incidents
GET    /api/v1/tickets/{ticket_id}

POST   /api/v1/tickets
POST   /api/v1/refunds/request             # creates a PENDING_APPROVAL refund request
POST   /api/v1/accounts/unlock             # only succeeds if the account is LOCKED
POST   /api/v1/entitlements/refresh        # re-syncs entitlement to the current plan
```

All three sensitive POST actions above are implemented with real logic in the service
layer (`app/services/`), validate state before acting, write an `audit_logs` entry, and
return `404`/`409` for missing resources or invalid states, respectively.

## What remains (later phases, per the spec)

Per `CloudDesk_Multi_Agent_Project_Spec.md` §31, everything beyond Phase 1 is
intentionally not built yet:

- **Phase 2 — Tool layer:** billing/account/technical/product tools wrapping this
  backend's services for agent use.
- **Phase 3 — Agents:** Triage, Billing, Account, Technical, Product, Resolution, QA,
  Escalation agents (LangChain/OpenRouter-backed, structured outputs).
- **Phase 4 — LangGraph:** shared state, dynamic routing, parallel specialist execution,
  reflection loop.
- **Phase 5 — Human-in-the-loop:** pause/resume approval workflow wired into the graph
  (the refund-request/account-unlock/entitlement-refresh primitives built in Phase 1 are
  what this will call).
- **Phase 6 — Product RAG:** pgvector-backed knowledge base + retrieval for the Product
  Agent.
- **Phase 7 — Observability:** agent run/tool-call tracing.
- **Phase 8 — Evaluation:** synthetic ticket dataset + metrics runner.
- **Phase 9 — Frontend:** Next.js customer portal + internal support console.
- **Phase 10 — Production:** deployment hardening, rate limiting, auth.
