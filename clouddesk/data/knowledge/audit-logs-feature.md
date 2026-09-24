---
document_id: audit-logs-feature
title: Audit Logs (Business and Enterprise)
category: feature documentation
product: CloudDesk Platform
version: "1.0"
source: docs/features/audit-logs.md
updated_at: 2026-04-22
---

# Audit Logs (Business and Enterprise)

Audit logs are an immutable record of sensitive actions taken on a CloudDesk organization's
accounts and billing — for example, account unlocks, refund approvals, entitlement
refreshes, and permission changes. The `audit_logs` feature is included on the Business and
Enterprise plans.

## What gets logged

CloudDesk logs the actor, the action type, the affected record, and a timestamp for every
sensitive operation, whether it was performed by a human support agent, an AI agent's tool
call, or a customer themselves through a self-service flow (e.g. an account unlock after
identity verification). Raw secrets (passwords, API key secrets) are never written to the
audit log.

## Why it matters for compliance

Audit logs give an organization administrator a reviewable trail for internal compliance and
security reviews — for example, confirming that every refund in a given month went through
proper approval, or that account unlocks were preceded by identity verification.

## Accessing audit logs

Audit logs are visible to organization administrators from the dashboard. They are not
customer-facing in the support chat; the AI Support agents use audit-relevant tool calls
internally (e.g. logging a refund request's creation) but do not expose raw audit log
contents to the end customer in chat responses.
