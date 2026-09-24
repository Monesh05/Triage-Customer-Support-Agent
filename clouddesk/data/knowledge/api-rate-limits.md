---
document_id: api-rate-limits
title: API Rate Limits by Plan
category: API documentation
product: CloudDesk API
version: "1.1"
source: docs/api/rate-limits.md
updated_at: 2026-07-20
---

# API Rate Limits by Plan

Each CloudDesk subscription has a monthly API request allowance tied to its plan:

- Free: 1,000 requests/month
- Pro: 50,000 requests/month
- Business: 250,000 requests/month
- Enterprise: 2,000,000 requests/month (custom limits available by contract)

## How usage is measured

Usage is tracked per customer in monthly periods (`period_start` to `period_end`) and
counted per successful API call. Requests that fail authentication (401) are not counted
against the rate limit; requests that succeed but return an application-level error may
still count, since they consumed backend capacity.

## What happens when you exceed your limit

Once a customer's usage for the current period reaches their plan's rate limit, further API
requests return `429 Too Many Requests` until the next period starts or the customer
upgrades to a plan with a higher limit. CloudDesk does not silently throttle or degrade
responses — the behavior at the limit is a hard, explicit rejection so client applications
can handle it predictably.

## Checking current usage

Current-period usage is visible on the dashboard's "Usage" page, and is one of the first
things the Technical Support Agent checks when investigating unexpected `403`/`429`
responses, since a stale-looking entitlement is sometimes actually a rate-limit issue rather
than a plan-sync issue.
