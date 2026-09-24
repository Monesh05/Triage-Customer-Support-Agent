---
document_id: troubleshooting-403-errors
title: Diagnosing 403 API Errors
category: troubleshooting
product: CloudDesk API
version: "1.0"
source: docs/troubleshooting/403-errors.md
updated_at: 2026-08-05
---

# Diagnosing 403 API Errors

A `403 Forbidden` response means the API key used is valid and active, but the request is
not entitled to the resource it's calling. This is different from `401 Unauthorized`, which
means the key itself is missing, malformed, revoked, or expired.

## Most common cause: stale plan entitlement

The most common cause of an unexpected `403` right after upgrading a subscription is that
the customer's live API entitlement has not yet synced to match the new plan. When a
subscription changes plan, the enforced rate limit and feature flags are refreshed
asynchronously and are normally expected to sync within about 5 minutes. If it has been
longer than that, the entitlement can be refreshed manually via
`POST /api/v1/entitlements/refresh`.

## Other causes to rule out first

Before assuming a stale entitlement, confirm: (1) there is no active service incident
affecting the API — an active outage can also present as unexpected error responses and
should not be misdiagnosed as an entitlement problem; (2) the API key's status is `active`,
not `revoked`/`expired`; (3) the customer isn't simply over their plan's rate limit, which
returns `429`, not `403` — a `403` specifically indicates an entitlement/permission mismatch.

## What Technical Support checks

When investigating a `403` report, CloudDesk's Technical Support Agent checks, in order:
active incidents, the API key's status, current usage against the rate limit, and finally
whether the subscription's plan and the account's actual entitlement agree. A mismatch
between subscription plan and entitlement is reported to the Account Agent for confirmation
and, if confirmed, an entitlement refresh is recommended.
