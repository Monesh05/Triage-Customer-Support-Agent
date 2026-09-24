---
document_id: billing-policy-duplicate-charges
title: Billing Policy — Duplicate Charges
category: billing policy
product: CloudDesk Billing
version: "1.0"
source: docs/policy/billing-duplicate-charges.md
updated_at: 2026-06-25
---

# Billing Policy — Duplicate Charges

Occasionally a billing-period charge is processed twice due to a retry or payment-provider
timing issue, resulting in two successful payments for the same subscription period. This is
a recognized, known failure mode, not something a customer needs to prove is "wrong" with
their account.

## Policy

When two successful payments exist for the same customer, subscription, and billing period,
the duplicate is eligible for a full refund of the extra charge. This is a `billing policy`
matter handled by the Billing Agent, distinct from the general refund eligibility window
described in the refund policy — a confirmed duplicate charge does not need to fall within
any particular time window to qualify.

## Approval requirement

Refunding a duplicate charge still requires human approval before the refund is actually
processed — the Billing Agent can identify the duplicate and create a refund *request*, but
it can never mark a refund as completed itself. Customers should be told a refund request
was created and is pending approval, never that the refund has already happened, unless a
refund tool result confirms it succeeded.

## Evidence CloudDesk requires

A duplicate-charge refund request cites both payment record identifiers (e.g. `PAY_123` and
`PAY_124`) as evidence. This traceability is required before an approver can act on the
request.
