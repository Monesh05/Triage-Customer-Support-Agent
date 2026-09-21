# CloudDesk — Multi-Agent Customer Support Platform

## 1. Project Overview

Build **CloudDesk**, a fictional B2B SaaS product with an embedded AI customer-support system.

The purpose of this project is to demonstrate a **genuine multi-agent architecture using LangGraph**.

This is NOT a single support agent with many tools.

The system must contain multiple specialized agents with:

- clearly separated responsibilities
- separate prompts
- restricted tool access
- structured outputs
- shared LangGraph state
- dynamic routing
- parallel execution where appropriate
- agent-to-agent collaboration
- critic/QA validation
- human-in-the-loop approvals
- escalation workflows
- observability
- evaluation

The AI support system operates on top of the CloudDesk SaaS backend and interacts with it through safe application APIs/tools.

The project should be portfolio-quality and suitable for discussion in an AI Engineer interview.

---

# 2. Core Product Concept

CloudDesk is a fictional SaaS platform that provides:

- user accounts
- organizations
- subscriptions
- pricing plans
- payments
- invoices
- API keys
- API usage
- product features
- service incidents
- customer support tickets

Customers can use CloudDesk and contact AI Support through an embedded chat interface.

The AI support team investigates the customer's problem using real application state.

Example:

> "I upgraded to Pro yesterday, got charged twice, and now my API requests are returning 403."

The system should recognize this as a multi-intent issue and coordinate:

- Billing Agent
- Account Agent
- Technical Agent

Those agents investigate independently and in parallel when possible.

Their findings are passed to a Resolution Agent.

A QA/Critic Agent validates the resolution.

If the QA check fails, the workflow loops back for correction.

If the system cannot safely resolve the issue, it creates a structured human escalation.

---

# 3. Main Architectural Principle

The most important requirement:

## This must be a TRUE multi-agent system.

Do NOT implement:

```text
User
  ↓
One LLM
  ↓
15 tools
  ↓
Answer
```

Instead implement:

```text
Customer
   ↓
Triage Agent
   ↓
Orchestrator / LangGraph
   ↓
Specialized Agents
   ├── Billing Agent
   ├── Account Agent
   ├── Technical Agent
   └── Product Agent
   ↓
Resolution Agent
   ↓
QA / Critic Agent
   ↓
Human Approval when required
   ↓
Final Response / Escalation
```

Each specialist must have its own:

- system prompt
- responsibilities
- tools
- output schema
- failure handling

Agents should NOT have access to unrelated tools.

---

# 4. Technology Stack

## Backend

- Python 3.12+
- FastAPI
- LangGraph
- LangChain where useful
- Pydantic v2
- SQLAlchemy
- PostgreSQL
- pgvector
- Redis where useful
- pytest

## LLM

Use **OpenRouter** as the model gateway.

Make the model configurable through environment variables.

Do not hard-code a specific model throughout the application.

Example:

```env
OPENROUTER_API_KEY=
OPENROUTER_MODEL=
```

Use an OpenAI-compatible client/interface where appropriate so models can be swapped easily.

## Frontend

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui

## Infrastructure

- Docker
- docker-compose for local development

Potential production deployment:

- Vercel for frontend
- Railway/Render/Fly.io or similar for backend
- managed PostgreSQL

Do not optimize for deployment until the local system is working.

---

# 5. CloudDesk Domain Model

Create a realistic but manageable SaaS backend.

Required entities:

```text
customers
organizations
accounts
plans
subscriptions
payments
invoices
api_keys
usage_records
products
service_incidents
support_tickets
support_policies
audit_logs
```

## Customer

Fields:

```text
id
name
email
organization_id
created_at
status
```

## Account

Fields:

```text
id
customer_id
status
mfa_enabled
failed_login_attempts
last_login_at
last_login_ip
permissions
```

## Plan

Fields:

```text
id
name
price_monthly
api_rate_limit
features
```

Example plans:

```text
Free
Pro
Business
Enterprise
```

## Subscription

Fields:

```text
id
customer_id
plan_id
status
start_date
renewal_date
```

## Payment

Fields:

```text
id
customer_id
subscription_id
amount
currency
status
payment_method
created_at
transaction_reference
```

## Invoice

Fields:

```text
id
customer_id
subscription_id
amount
status
issued_at
due_at
```

## API Key

Fields:

```text
id
customer_id
key_hash
status
created_at
last_used_at
rate_limit
```

Never expose raw API secrets unnecessarily.

## Usage

Fields:

```text
id
customer_id
api_calls
period_start
period_end
```

## Service Incident

Fields:

```text
id
service_name
status
severity
started_at
resolved_at
description
```

## Support Ticket

Fields:

```text
id
customer_id
subject
description
status
priority
created_at
updated_at
assigned_to
```

## Support Policy

Store policies such as:

- refund rules
- cancellation rules
- plan upgrade behavior
- account recovery rules
- escalation rules

---

# 6. Seed Data

Create realistic seed data.

Do not create only happy-path records.

Include:

### Normal customers

Customers with healthy accounts.

### Duplicate payments

At least several customers with two successful payments for the same billing period.

### Failed payments

Customers with failed or pending payments.

### Subscription mismatch

Customers whose subscription says Pro but API entitlement is stale.

### Locked accounts

Customers with repeated failed logins.

### Active service incidents

Examples:

```text
API degraded
Authentication degraded
Billing delayed
```

### False-positive scenarios

Create customers whose unusual activity is legitimate.

The system must not escalate every unusual event.

---

# 7. Backend API

Build a normal FastAPI backend for CloudDesk.

Example endpoints:

```text
GET    /api/v1/customers/{customer_id}
GET    /api/v1/accounts/{customer_id}
GET    /api/v1/subscriptions/{customer_id}
GET    /api/v1/payments/{customer_id}
GET    /api/v1/invoices/{customer_id}
GET    /api/v1/usage/{customer_id}
GET    /api/v1/api-keys/{customer_id}
GET    /api/v1/incidents
GET    /api/v1/tickets/{ticket_id}

POST   /api/v1/tickets
POST   /api/v1/refunds/request
POST   /api/v1/accounts/unlock
POST   /api/v1/entitlements/refresh
```

Sensitive actions must have explicit authorization and approval handling.

---

# 8. Tool Layer

Agents must not directly access PostgreSQL.

Use application-level tools.

Architecture:

```text
Agent
  ↓
Tool
  ↓
Service Layer
  ↓
Database
```

Examples:

```python
get_customer()
get_subscription()
get_payment_history()
get_invoice()
get_account()
get_login_history()
get_account_permissions()
get_subscription_entitlements()
get_api_usage()
get_api_key_status()
get_service_status()
search_error_logs()
get_recent_incidents()
get_billing_policy()
search_product_docs()
calculate_refund()
create_refund_request()
refresh_entitlement()
```

Tools must:

- validate inputs
- return structured results
- handle errors
- avoid exposing secrets
- log important actions
- enforce authorization rules

---

# 9. Agent Team

## 9.1 Triage Agent

### Responsibility

The Triage Agent only:

- understands the customer message
- identifies intents
- determines priority
- determines sentiment
- determines which specialist agents are needed
- identifies obvious escalation signals

It must NOT solve the issue.

Example:

Customer:

> "I was charged twice and my API stopped working after upgrading."

Output:

```json
{
  "intents": ["billing", "technical", "account"],
  "priority": "high",
  "sentiment": "frustrated",
  "required_agents": [
    "billing",
    "technical",
    "account"
  ],
  "reason": "The customer reports a duplicate charge and an API entitlement/access problem following a subscription upgrade."
}
```

Use structured Pydantic output.

---

# 10. Billing Agent

## Responsibility

Only investigate:

- subscriptions
- payments
- invoices
- duplicate charges
- refunds
- billing policy
- cancellations

## Allowed tools

```text
get_subscription
get_payment_history
get_invoice
calculate_refund
get_billing_policy
create_refund_request
```

## Example

Customer:

> "I was charged twice."

Billing Agent should investigate the actual payment records.

It should produce structured findings:

```json
{
  "status": "resolved",
  "findings": [
    {
      "fact": "Two successful payments of $49 exist for the same billing period."
    }
  ],
  "recommended_actions": [
    {
      "action": "refund",
      "amount": 49,
      "requires_approval": true
    }
  ],
  "evidence": [
    "PAY_123",
    "PAY_124"
  ]
}
```

It must NOT claim that a refund occurred unless the refund tool actually succeeded.

---

# 11. Account Agent

## Responsibility

Investigate:

- account access
- login issues
- MFA
- permissions
- account status
- subscription entitlements

## Allowed tools

```text
get_account
get_login_history
get_account_permissions
get_subscription_entitlements
check_mfa_status
```

Example:

> "I can't access the Pro API."

The Account Agent can determine:

```text
subscription = PRO
entitlement = FREE
```

and report an entitlement mismatch.

---

# 12. Technical Support Agent

## Responsibility

Investigate:

- API errors
- application errors
- service availability
- usage/rate limits
- API key status
- known incidents

## Allowed tools

```text
get_api_usage
get_api_key_status
get_service_status
search_error_logs
get_recent_incidents
search_product_docs
```

It should form hypotheses and gather evidence before making a recommendation.

Example:

```text
Hypothesis:
API 403 is caused by stale subscription entitlement.

Evidence:
- Customer subscription is Pro.
- API entitlement is Free.
- No active API outage.
- API key is active.
```

---

# 13. Product Agent

## Responsibility

Answer product/documentation questions.

It should use the product knowledge base.

Examples:

> "Does Pro support 100,000 API requests?"

> "How does MFA work?"

> "How do I rotate an API key?"

RAG is a capability of this specialist agent.

Do NOT make the entire system a generic RAG chatbot.

---

# 14. Product RAG

Create a small knowledge base.

Documents:

```text
product documentation
pricing
API documentation
troubleshooting
billing policy
refund policy
account recovery
feature documentation
```

Use:

- embeddings
- PostgreSQL
- pgvector
- metadata filtering

Metadata should include:

```text
document_id
title
category
product
version
source
updated_at
```

The Product Agent retrieves relevant information.

The final answer should retain source metadata where appropriate.

---

# 15. Resolution Agent

The Resolution Agent receives the outputs of specialist agents.

It should:

- synthesize findings
- identify contradictions
- distinguish facts from recommendations
- identify unresolved issues
- construct a proposed resolution
- generate a customer-facing response draft

It should NOT independently invent facts.

Example input:

```text
Billing:
Duplicate payment confirmed.
Refund recommended.

Technical:
API 403 caused by stale entitlement.

Account:
Subscription is Pro.
Entitlement is Free.
```

Output:

```text
Two separate issues were identified:

1. Duplicate billing of $49.
2. API entitlement has not synchronized with the Pro subscription.

A refund request should be created for the duplicate payment.
The API entitlement should be refreshed.

Refund processing requires approval.
```

---

# 16. QA / Critic Agent

This agent is mandatory.

It reviews every proposed resolution before it reaches the customer.

Check:

1. factual accuracy
2. evidence support
3. completeness
4. policy compliance
5. hallucinations
6. incorrect promises
7. whether an action actually happened
8. whether sensitive actions require approval
9. tone
10. whether escalation is needed

Example:

```json
{
  "approved": false,
  "issues": [
    "The response says the refund was processed, but only a refund request was created."
  ],
  "required_changes": [
    "State that the refund request was created and is pending approval."
  ]
}
```

---

# 17. Escalation Agent

Escalate when:

- issue cannot be resolved
- confidence is low
- policy requires a human
- action requires human approval and approval is unavailable
- repeated QA failures occur
- customer requests a human
- sensitive situation requires manual review

Create a structured handoff:

```text
Customer
Issue
Intent
Priority
Investigation performed
Evidence
Actions attempted
Unresolved questions
Recommended human action
Conversation history
```

Never simply tell the customer:

> "Contact support."

Create a useful internal handoff.

---

# 18. LangGraph State

Use a typed state.

Example:

```python
class SupportState(TypedDict):

    customer_id: str
    customer_message: str
    conversation_history: list

    intents: list[str]
    priority: str
    sentiment: str
    required_agents: list[str]

    specialist_results: dict

    resolution: dict | None
    qa_result: dict | None

    escalation_required: bool
    human_approval_required: bool

    pending_actions: list
    approved_actions: list
    executed_actions: list

    errors: list[str]

    iteration: int
```

Use structured models where appropriate.

---

# 19. LangGraph Workflow

Implement a proper StateGraph.

High-level workflow:

```text
START
  ↓
Triage
  ↓
Dynamic Router
  ↓
Parallel Specialist Agents
  ├── Billing
  ├── Account
  ├── Technical
  └── Product
  ↓
Resolution
  ↓
QA
  ↓
Approved?
 ├── YES → Check Actions
 │           ↓
 │        Approval Required?
 │        ├── YES → Human Approval
 │        └── NO  → Execute
 │
 └── NO → Resolution
              ↓
             QA
```

If the issue cannot be resolved:

```text
Specialists
  ↓
Resolution
  ↓
QA
  ↓
Escalation
  ↓
Human Queue
```

---

# 20. Parallel Agent Execution

This is a key requirement.

For:

> "I was charged twice and my API isn't working."

Do not execute:

```text
Billing → Technical → Account
```

sequentially if there are no dependencies.

Instead execute:

```text
             Triage
                ↓
       ┌────────┼────────┐
       ↓        ↓        ↓
    Billing  Technical Account
       └────────┼────────┘
                ↓
            Resolution
```

Use LangGraph's graph/state mechanisms appropriately.

---

# 21. Reflection Loop

Implement:

```text
Resolution
    ↓
QA
    ↓
Approved?
   / \
 NO   YES
 |     |
 ↓     ↓
Resolution  Final
```

Maximum iterations:

```python
MAX_ITERATIONS = 3
```

Prevent infinite loops.

If the workflow still fails after the maximum attempts:

```text
Escalation Agent
```

---

# 22. Human-in-the-Loop

Sensitive actions require approval.

Examples:

- refund
- account unlock
- subscription modification
- security setting changes
- customer data changes

Workflow:

```text
Billing Agent
      ↓
Refund Recommendation
      ↓
Human Approval
   /        \
Approve    Reject
  ↓          ↓
Execute     Explain
```

Use LangGraph interruption/checkpoint mechanisms where appropriate so execution can pause and resume.

---

# 23. Example Scenarios

Implement and test at least these.

## Scenario A — Simple FAQ

> "Does Pro include API access?"

Expected:

```text
Triage
 ↓
Product Agent
 ↓
QA
 ↓
Response
```

## Scenario B — Duplicate Payment

> "Why was I charged twice?"

Expected:

```text
Triage
 ↓
Billing Agent
 ↓
Resolution
 ↓
QA
 ↓
Refund approval if necessary
```

## Scenario C — Account Lockout

> "I can't log into my account."

Expected:

```text
Triage
 ↓
Account Agent
 ↓
Resolution
 ↓
QA
```

## Scenario D — API Failure

> "My API returns 403."

Expected:

```text
Triage
 ↓
Technical + Account
 ↓
Resolution
 ↓
QA
```

## Scenario E — Multi-Intent

> "I upgraded yesterday, got charged twice, and now my API doesn't work."

Expected:

```text
Triage
 ↓
Billing ──────┐
Account ──────┼──→ Resolution → QA
Technical ────┘
```

## Scenario F — Active Outage

> "My API is failing."

Technical Agent should check the incident system.

If an active outage exists, do not invent an account-level explanation.

## Scenario G — Human Escalation

Customer explicitly asks:

> "I want to speak to a human."

System should prepare an escalation rather than forcing an AI resolution.

---

# 24. Agent Observability

Record each agent execution.

Store:

```text
run_id
ticket_id
agent_name
start_time
end_time
duration
status
input_summary
output_summary
tool_calls
tool_results
error
iteration
```

Create an execution trace.

Example:

```text
Triage Agent          ✓ 1.2s
Billing Agent         ✓ 2.8s
Technical Agent       ✓ 3.1s
Account Agent         ✓ 1.9s
Resolution Agent      ✓ 1.4s
QA Agent              ✗ 0.9s
Resolution Agent      ✓ 1.2s
QA Agent              ✓ 0.8s
```

Never log secrets, passwords, API keys, or unnecessary personal data.

---

# 25. Frontend

Build two interfaces.

## Customer Portal

Pages:

```text
/dashboard
/billing
/usage
/api
/support
```

The Support page should contain the AI support chat.

Show useful progress:

```text
AI Support Team

✓ Understanding request
✓ Checking billing
✓ Checking account
✓ Checking API status
⟳ Preparing resolution
```

Do not expose private chain-of-thought.

Show only safe high-level agent status and tool/action summaries.

---

# 26. Internal Support Console

Create:

```text
/support-console
```

Views:

### Tickets

List:

```text
Ticket
Customer
Priority
Intent
Status
Assigned agents
```

### Ticket Detail

Show:

- customer message
- detected intent
- specialist findings
- evidence
- resolution
- QA result
- pending approval
- escalation

### Agent Trace

Show the execution sequence:

```text
Triage
 ↓
Billing
 ↓
Technical
 ↓
Resolution
 ↓
QA
```

### Approval Queue

Example:

```text
Refund $49

Reason:
Duplicate payment.

Evidence:
PAY_123
PAY_124

[Approve] [Reject]
```

---

# 27. Security Requirements

Implement basic security practices.

- Environment variables for secrets
- Never commit `.env`
- `.env.example`
- Authentication for customer/support APIs
- Authorization for sensitive operations
- Agent-specific tool permissions
- Input validation
- SQLAlchemy parameterization
- No arbitrary SQL tool
- No arbitrary shell tool
- Audit sensitive actions
- Never expose secrets to the LLM
- Never expose raw passwords/API keys
- Never claim an action succeeded unless the tool returned success

---

# 28. Evaluation

Create at least 100 synthetic support tickets.

Categories:

```text
billing
account
technical
product
multi-intent
ambiguous
escalation
false-positive
policy-sensitive
adversarial
```

Measure:

```text
Intent classification accuracy
Routing accuracy
Tool-call accuracy
Resolution accuracy
QA accuracy
Escalation accuracy
Hallucination rate
Average latency
Average number of agent iterations
```

Create:

```bash
python -m evaluation.run_eval
```

Do not fabricate evaluation numbers.

Only report metrics generated by the actual evaluation system.

---

# 29. Testing

Write unit tests for:

- tools
- database services
- routing
- structured outputs
- policy checks

Write integration tests for:

- billing workflow
- account workflow
- technical workflow
- multi-intent workflow
- QA retry
- human approval
- escalation

Test failure scenarios.

Examples:

- tool timeout
- malformed model output
- unavailable database
- unknown intent
- QA repeatedly failing
- action execution failure

---

# 30. Project Structure

Use a clean modular structure similar to:

```text
clouddesk/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── agents/
│   │   │   ├── triage.py
│   │   │   ├── billing.py
│   │   │   ├── account.py
│   │   │   ├── technical.py
│   │   │   ├── product.py
│   │   │   ├── resolution.py
│   │   │   ├── qa.py
│   │   │   └── escalation.py
│   │   │
│   │   ├── graph/
│   │   │   ├── state.py
│   │   │   ├── graph.py
│   │   │   ├── nodes.py
│   │   │   └── routing.py
│   │   │
│   │   ├── tools/
│   │   │   ├── billing.py
│   │   │   ├── account.py
│   │   │   ├── technical.py
│   │   │   └── product.py
│   │   │
│   │   ├── services/
│   │   ├── database/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── rag/
│   │   ├── observability/
│   │   └── config.py
│   │
│   └── tests/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── dashboard/
│   ├── support/
│   ├── agent-trace/
│   └── approvals/
│
├── evaluation/
│   ├── datasets/
│   ├── metrics/
│   └── run_eval.py
│
├── data/
│   ├── knowledge/
│   └── seed/
│
├── docker-compose.yml
├── .env.example
├── README.md
└── Makefile
```

You may improve this structure if there is a strong engineering reason.

---

# 31. Development Phases

Do NOT build the whole application in one pass.

## Phase 1 — CloudDesk Backend

Build:

- FastAPI
- PostgreSQL
- SQLAlchemy models
- migrations
- seed data
- basic REST APIs
- tests

Verify the simulated SaaS backend works independently.

---

## Phase 2 — Tool Layer

Build:

- billing tools
- account tools
- technical tools
- product tools

Test tools independently.

---

## Phase 3 — Agents

Build:

- Triage Agent
- Billing Agent
- Account Agent
- Technical Agent
- Product Agent
- Resolution Agent
- QA Agent
- Escalation Agent

Each agent must be independently testable.

---

## Phase 4 — LangGraph

Implement:

- shared state
- dynamic routing
- parallel execution
- resolution
- QA
- reflection loop
- escalation

Test the graph using predefined scenarios.

---

## Phase 5 — Human-in-the-Loop

Implement:

- pending actions
- approval state
- pause/resume
- approval API
- audit log

---

## Phase 6 — Product RAG

Implement:

- document ingestion
- chunking
- embeddings
- pgvector
- retrieval
- Product Agent integration
- source metadata

---

## Phase 7 — Observability

Implement:

- agent runs
- tool calls
- latency
- errors
- execution traces

---

## Phase 8 — Evaluation

Implement:

- synthetic ticket dataset
- evaluation runner
- metrics
- regression tests

---

## Phase 9 — Frontend

Build:

- customer portal
- support chat
- support console
- agent trace
- approval queue

---

## Phase 10 — Production

Add:

- Docker
- production configuration
- authentication
- authorization
- rate limiting
- logging
- deployment
- README
- architecture diagram

---

# 32. Development Rules for Claude Code

Before implementing anything:

1. Inspect the repository.
2. Identify the current environment and existing files.
3. Create an architecture plan.
4. Identify dependencies.
5. Identify potential risks.
6. Then implement only Phase 1.

Do not build all phases at once.

After each phase:

1. Run tests.
2. Run lint/type checks where configured.
3. Fix errors.
4. Verify the application.
5. Summarize what was built.
6. Explain what remains.
7. Wait for the next phase instruction.

Do not create fake implementations.

Do not silently skip requirements.

Do not add unnecessary frameworks.

Prefer simple, modular, maintainable code.

Do not hard-code secrets.

Do not expose chain-of-thought in the UI or logs.

Do not allow agents unrestricted database or shell access.

---

# 33. Definition of Done

The final project should demonstrate:

- [ ] Real CloudDesk SaaS backend
- [ ] PostgreSQL
- [ ] realistic seed data
- [ ] application-level APIs/tools
- [ ] multiple specialized agents
- [ ] restricted tools per agent
- [ ] LangGraph orchestration
- [ ] dynamic routing
- [ ] parallel specialist execution
- [ ] structured outputs
- [ ] Resolution Agent
- [ ] QA/Critic Agent
- [ ] reflection loop
- [ ] human-in-the-loop
- [ ] escalation workflow
- [ ] Product RAG
- [ ] observability
- [ ] agent execution traces
- [ ] evaluation framework
- [ ] automated tests
- [ ] customer-facing UI
- [ ] internal support console
- [ ] Docker setup
- [ ] production deployment documentation

The final result should clearly demonstrate:

> **A team of specialized AI agents collaborating through LangGraph to investigate, resolve, validate, and safely act on customer-support issues.**

The project should NOT feel like a chatbot with tools.

It should feel like an **AI support operations platform**.

---

# 34. Start Now

First inspect the repository.

Then provide:

1. proposed architecture
2. directory structure
3. dependencies
4. database schema
5. Phase 1 implementation plan
6. risks and design decisions

Do NOT implement Phase 2 or later yet.

After presenting the plan, begin implementing **Phase 1 only**.
