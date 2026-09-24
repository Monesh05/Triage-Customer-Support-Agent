# CloudDesk — AI-Powered Multi-Agent Customer Support Platform

CloudDesk is a fictional B2B SaaS product used as the vehicle for a complete, working
multi-agent AI customer-support system: a LangGraph-orchestrated team of specialist agents
that triages, investigates, resolves, and (when necessary) escalates or seeks human
approval for real customer support requests — backed by a real FastAPI + PostgreSQL
application, a real Next.js customer portal and internal support console, retrieval-
augmented product documentation search, full agent observability/tracing, an evaluation
harness, and production-hardening (authentication, rate limiting, security headers).

The full project vision and every phase's detailed requirements live in
`CloudDesk_Multi_Agent_Project_Spec.md`. **This README describes the system as it actually
exists today — all 10 phases implemented.**

## What this project demonstrates

Built as a portfolio/interview piece, this repository is a working demonstration of:

- **Multi-agent orchestration with LangGraph**: a triage agent classifies intent and fans
  out to 1-4 parallel specialist agents (billing, account, technical, product), which
  converge on a resolution agent, a QA/reflection loop that can bounce a resolution back
  for revision (bounded, guaranteed to converge), and an escalation path — a real
  `StateGraph`, not a scripted demo.
- **Human-in-the-loop (HITL)**: LangGraph's `interrupt()`/checkpoint mechanism genuinely
  pauses a run mid-graph when a specialist recommends an action requiring approval (e.g. a
  refund), persists it to a real approval queue, and resumes the exact paused run once a
  human (or the Support Console UI) decides — not a fake "pending" status with no real
  pause.
- **Retrieval-augmented generation**: product documentation is chunked, embedded
  (`text-embedding-3-small`), stored in pgvector, and retrieved by similarity for the
  Product specialist agent, with a real "not found" path when nothing clears the
  similarity threshold (no hallucinated citations).
- **Agent observability**: every agent/node execution is traced (inputs/outputs redacted
  and truncated, tool calls and results recorded, duration/status/errors) and queryable per
  ticket or per run — the same trace data powers both the Support Console's debugging view
  and the evaluation harness's automated checks.
- **A real evaluation harness**: a dataset of support scenarios is run through the actual
  `run_support_workflow` (no mocks) and scored against expected outcomes/tool calls/policy
  compliance — this is how regressions in agent behavior get caught, not just unit tests of
  isolated functions.
- **Production hardening**: JWT authentication with a real customer-vs-staff authorization
  boundary (fixing what was, before this phase, a wide-open IDOR on every endpoint), rate
  limiting, security headers, request-id-correlated structured logging, and a real login UI
  on the frontend.
- **Full-stack delivery**: a Next.js 16 customer portal (dashboard, billing, usage, API
  keys, AI support chat) and a separate internal Support Console (ticket list, agent trace
  viewer, approval queue) — both real, working UIs against the real backend, not mockups.

## Architecture

```text
┌─────────────────────────┐        ┌──────────────────────────┐
│   Customer Portal        │        │   Support Console         │
│   (Next.js, /login →     │        │   (Next.js, /support-     │
│   dashboard/billing/     │        │   console/login → ticket  │
│   usage/API keys/AI chat)│        │   list/trace/approvals)   │
└────────────┬─────────────┘        └─────────────┬────────────┘
             │  fetch (server: direct+Bearer;      │
             │  browser: via /api/backend proxy)   │
             └──────────────────┬───────────────────┘
                                 │  Authorization: Bearer <JWT>
                                 ▼
                    ┌─────────────────────────┐
                    │   FastAPI (app/main.py)  │
                    │  CORS · security headers │
                    │  · request-id · rate      │
                    │  limit · JWT auth deps    │
                    └────────────┬──────────────┘
                                 │
        ┌────────────────────────┼─────────────────────────┐
        ▼                        ▼                          ▼
┌───────────────┐   ┌─────────────────────────┐   ┌──────────────────┐
│ CRUD API       │   │ Conversation API         │   │ Approval / Trace  │
│ (customers,    │   │ (POST /conversations,    │   │ API (staff-only)  │
│ billing, etc.) │   │ GET .../{thread_id})      │   │                   │
└───────┬────────┘   └────────────┬─────────────┘   └─────────┬────────┘
        │                         ▼                            │
        │           ┌─────────────────────────────┐            │
        │           │  LangGraph StateGraph         │            │
        │           │  START → triage               │            │
        │           │    → [billing|account|        │◄───────────┘
        │           │       technical|product]*      │  resume_support_workflow
        │           │    → resolution → qa           │  (after a human decision)
        │           │    → (loop | escalation |      │
        │           │       finalize)                 │
        │           │    → await_human_decision→END  │
        │           └──────────────┬──────────────────┘
        │                          │  each specialist calls its own tool layer
        │                          ▼
        │           ┌─────────────────────────────┐
        │           │  Tools (billing/account/      │
        │           │  technical/product) — each     │
        │           │  agent only gets its own tools │
        │           └──────────────┬──────────────────┘
        │                          ▼
        └─────────────► ┌─────────────────────────────┐
                         │  Services (business logic)   │
                         │  + audit log + observability  │
                         └──────────────┬──────────────────┘
                                        ▼
                         ┌─────────────────────────────┐
                         │  PostgreSQL (+ pgvector for   │
                         │  Product RAG embeddings)      │
                         └─────────────────────────────┘
```

## Repository layout

```text
clouddesk/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── agents/          # triage, billing, account, technical, product, resolution, qa, escalation
│   │   ├── tools/            # per-domain tool layer (billing/account/technical/product) agents call
│   │   ├── graph/            # LangGraph StateGraph: nodes, routing, state, pause/resume
│   │   ├── rag/               # Product RAG: chunking, embeddings, pgvector retrieval
│   │   ├── observability/     # Phase 7 agent-run tracing
│   │   ├── llm/                # OpenAI/OpenRouter client wrapper
│   │   ├── api/v1/             # REST routers (auth, customers, billing, conversations, approvals, traces, ...)
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic v2 request/response schemas
│   │   ├── services/           # Business logic + audit logging + auth
│   │   ├── database/            # Engine/session/declarative base
│   │   ├── core/                 # Settings, logging, security (JWT/bcrypt), rate limiting, middleware
│   │   └── main.py               # FastAPI app entrypoint
│   ├── alembic/                  # Database migrations
│   ├── tests/                     # pytest suite (164+ tests; a few real-LLM `integration`-marked tests excluded by default)
│   └── Dockerfile
├── frontend/                 # Next.js 16 App Router (TypeScript, Tailwind, shadcn/ui)
│   ├── src/app/(portal)/      # Customer portal: dashboard, billing, usage, API keys, AI support chat
│   ├── src/app/support-console/(console)/  # Internal Support Console: tickets, trace viewer, approvals
│   ├── src/app/login, src/app/support-console/login  # Customer / staff login pages
│   ├── src/app/api/auth/*     # Route handlers proxying login/logout to the backend, setting the httpOnly JWT cookie
│   ├── src/app/api/backend/[...path]  # Same-origin proxy so client components can call the backend without exposing the JWT to JS
│   └── Dockerfile
├── data/seed/                 # Seed script: organizations, plans, ~40 demo customers, a demo staff account
├── evaluation/                 # Real end-to-end evaluation harness + its own test suite
├── docker-compose.yml
└── .env.example
```

## Running it locally

### 1. Database

```bash
docker compose up -d postgres
```

This starts only Postgres (pgvector-enabled), on host port **5433** (container 5432) — the
default port is deliberately non-standard so it never collides with a locally-installed
Postgres.

### 2. Backend

```bash
cd clouddesk/backend
python -m venv .venv && .venv/Scripts/activate   # or source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp ../../.env.example .env   # then fill in OPENAI_API_KEY/OPENROUTER_API_KEY and JWT_SECRET_KEY
alembic upgrade head
python -m data.seed.seed      # from clouddesk/backend, seeds ~40 demo customers + 1 staff account
uvicorn app.main:app --reload --port 8000
```

Environment variables (see `.env.example` for the full list with comments):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection string (asyncpg) |
| `LLM_PROVIDER`, `OPENROUTER_API_KEY`/`OPENAI_API_KEY`, `*_MODEL` | LLM gateway config — every agent call goes through `app/llm/client.py` |
| `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Auth token signing (Phase 10) — **must** be a real secret outside local dev |
| `RATE_LIMIT_LOGIN`, `RATE_LIMIT_CONVERSATIONS` | Per-client rate limits (Phase 10) |
| `CORS_ALLOWED_ORIGINS` | Comma-separated browser origins allowed to call the API |

### 3. Frontend

```bash
cd clouddesk/frontend
npm install
cp .env.local.example .env.local   # point NEXT_PUBLIC_API_BASE_URL at your backend
npm run dev
```

Visit `http://localhost:3000/login` for the customer portal, or
`http://localhost:3000/support-console/login` for the internal Support Console.

### 4. Evaluation harness

```bash
cd evaluation
python run_eval.py       # runs the dataset through the REAL run_support_workflow (real LLM calls, real DB)
python -m pytest tests   # the harness's own automated test suite (mocked, fast, part of normal CI)
```

### Full containerized run

```bash
docker compose up          # postgres + backend + frontend
docker compose up postgres # just the database, for local dev servers against it
```

## Authentication (Phase 10)

There is no real signup flow (this is a demo/portfolio app, not a production SaaS with paying
customers) — instead:

- **Customers** log in at `/login` with their seeded email and the shared demo password
  `demo1234` (the login page lists a few example emails). This calls
  `POST /api/v1/auth/login`, which verifies the password against a bcrypt hash and issues a
  short-lived (30 minute) JWT carrying `role: "customer"` and the customer's own id.
- **Staff** log in at `/support-console/login` with the seeded demo account
  (`staff@clouddesk.example` / `staff1234`), issuing a JWT with `role: "staff"` instead.
- Every customer-facing endpoint derives the acting customer id from the **token**, never
  from a client-supplied path/body parameter — a customer's JWT can only ever act as that
  customer (403 otherwise). Every internal endpoint (`/approvals`, `/traces`, the
  cross-customer `GET /tickets`) requires the staff role.
- The frontend stores the JWT in an **httpOnly cookie** (never `localStorage`, never
  readable by client-side JS). Server Components attach it directly; client components
  (the AI chat's polling, the Approval Queue's decision buttons) call a same-origin Next.js
  proxy route (`/api/backend/...`) that attaches it server-side instead.
- Login attempts (success and failure) are audited like every other sensitive action.

## Testing

- **Backend**: `pytest` (from `clouddesk/backend`, with `DATABASE_URL` pointed at a
  `clouddesk_test` database) — 170 tests, real Postgres, mocked LLM calls by default. A
  handful of `@pytest.mark.integration` tests make real LLM calls and are excluded from the
  default run; run them explicitly with `pytest -m integration`.
- **Evaluation**: `python -m pytest evaluation/tests` — 27 tests against the harness's
  scoring logic (mocked); `python run_eval.py` for the real end-to-end run.
- **Frontend**: `npm run build && npm run lint` — both clean.

## Production deployment notes

This repository has not been deployed to a live cloud service — the following is deployment
*guidance*, matching the spec's suggested targets (frontend on Vercel; backend + Postgres on
Railway/Render/Fly.io or similar).

- **Environment variables**: every value in `.env.example` needs a real production value —
  most importantly `JWT_SECRET_KEY` (the app refuses to start with the insecure default
  once `APP_ENV != "development"`), the real LLM provider API key, `DATABASE_URL` pointed
  at a managed Postgres instance with the `vector` extension available, and
  `CORS_ALLOWED_ORIGINS` set to the real deployed frontend origin.
- **Migrations on deploy**: run `alembic upgrade head` as a release step before the new
  backend version starts serving traffic, not from inside the running app.
- **LangGraph checkpointer**: the graph is compiled with an in-process `MemorySaver`
  (`app/graph/graph.py`) — paused human-in-the-loop runs do **not** survive a process
  restart. A real deployment needs a persistent checkpointer (e.g.
  `langgraph-checkpoint-postgres`, evaluated for CVEs/pinned like every other dependency)
  before HITL is safe to run with more than one backend instance or across restarts.
- **Conversation status registry**: similarly, `app/services/conversation_service.py`'s
  polling registry is in-process/in-memory — a multi-instance deployment needs this moved
  to shared storage (Redis, or the database) or sticky routing per `thread_id`.
- **`clouddesk_test` seed data**: the test database is schema-only (tables created fresh
  per test session, never seeded) — this is intentional for test isolation, but means there
  is no long-lived "staging with realistic data" database; use the seeded dev database (or
  a copy of it) for that.
- **Operational concerns**: aggregate the structured, request-id-tagged logs
  (`app/core/logging.py`) into a real log sink (e.g. CloudWatch, Datadog, an OpenSearch/ELK
  stack); manage secrets via the platform's secret manager rather than plain environment
  variables where available; size the asyncpg connection pool for expected concurrency
  under load; put the rate limiter's state in a shared store (e.g. Redis-backed `limits`
  storage) once running more than one backend instance, since the default in-memory limiter
  state does not share across processes.

## Definition of done — honest status

Referencing the spec's Definition of Done (section 33):

**Done:**
- All 10 phases implemented and working end-to-end against a real database and (when
  configured) a real LLM.
- Full multi-agent workflow: triage → parallel specialists → resolution → QA reflection
  loop (bounded, converges) → escalation/finalize → optional human-in-the-loop pause/resume.
- The Phase 5-era conversation-status-lag bug is fixed at its root cause: `finalize_node`
  sets `human_approval_required: True` but nothing ever reset it, since that field has no
  LangGraph reducer (overwrite-on-update, not merge) — `await_human_decision_node` now
  explicitly resets it to `False` on resume, so `GET /conversations/{id}` correctly reports
  `completed`/`escalated` instead of staying stuck on `awaiting_approval`. Covered by a
  regression test at both the graph layer and the conversation-service layer.
- Real authentication and authorization: JWT-based, bcrypt-hashed passwords, a genuine
  customer-vs-staff boundary enforced on every route, rate limiting on login and
  conversation-start, security headers, request-id-correlated logging, and a real login UI.
- 170 backend tests passing (one single-run flake observed under concurrent load on Windows
  — a connection-pool timing issue unrelated to this phase's changes, reproducibly passes in
  isolation), 27 evaluation tests passing, frontend build/lint clean.
- A full security review against spec section 27's checklist — see the implementation
  history for the itemized pass.

**Known limitations (by design, documented rather than silently accepted):**
- The LangGraph checkpointer and the conversation-status registry are both in-process/
  in-memory — neither survives a restart or scales past one backend instance without
  further work (see Production Deployment notes above).
- No live cloud deployment was performed — the Production Deployment section is guidance,
  not a verified runbook.
- The `clouddesk_test` database has no seed data by design (schema-only, fresh per test
  session); there is no separate "staging with realistic data" environment.
- Rate limiting state is in-process (via `slowapi`/`limits`), not shared across multiple
  backend instances.
- No refresh-token flow — a session simply expires after 30 minutes and the user logs in
  again, which is an intentional scope decision for a demo/portfolio app, not an oversight.
