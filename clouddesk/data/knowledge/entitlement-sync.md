---
document_id: entitlement-sync
title: How Plan Upgrades Sync to Your API Entitlement
category: troubleshooting
product: CloudDesk API
version: "1.0"
source: docs/troubleshooting/entitlement-sync.md
updated_at: 2026-08-05
---

# How Plan Upgrades Sync to Your API Entitlement

A subscription's plan (Free/Pro/Business/Enterprise) and a customer's live API entitlement
(the rate limit and feature flags actually enforced on requests) are tracked separately.
Changing a subscription's plan is immediate at the billing/record level, but the enforced
entitlement is expected to catch up asynchronously, normally within about 5 minutes.

## Symptoms of a stale entitlement

The classic symptom is: a customer upgrades from Free to Pro (or any lower-to-higher plan
change) and immediately afterward still gets `403 Forbidden` on API calls that should now be
allowed, or is still capped at the old plan's rate limit. This is an entitlement-sync delay,
not a billing failure — the payment and subscription change usually succeeded.

## Forcing a refresh

If more than about 5 minutes have passed since the plan change and the entitlement still
looks stale, it can be refreshed on demand via `POST /api/v1/entitlements/refresh`. This
recomputes the customer's enforced rate limit and feature flags directly from their current
subscription's plan, without requiring another billing event.

## When this is not the explanation

If there is an active service incident affecting the API or authentication, that is a more
likely explanation for unexpected errors than a stale entitlement, and should be checked
first — see "Diagnosing 403 API Errors."
