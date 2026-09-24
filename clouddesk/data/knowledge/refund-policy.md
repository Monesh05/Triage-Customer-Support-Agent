---
document_id: refund-policy
title: Refund Policy
category: refund policy
product: CloudDesk Billing
version: "1.0"
source: docs/policy/refunds.md
updated_at: 2026-06-25
---

# Refund Policy

Refund eligibility depends on the type of issue.

## Duplicate charges

A confirmed duplicate payment for the same subscription and billing period is eligible for a
full refund of the extra charge, without needing to fall inside the general refund window
described below (see "Billing Policy — Duplicate Charges" for details).

## General refund window

For other refund requests (e.g. a customer dissatisfied with the service, or billed for a
feature they didn't use), CloudDesk allows refund requests within 90 days of the original
charge. Requests made after the 90-day window are not eligible for a refund under standard
policy and require an escalation to a human for a case-by-case decision.

## Approval is always required

No refund is ever processed automatically by an AI agent. Every refund — whether a duplicate
charge or a within-window general request — must be created as a pending refund request and
approved by a human before money moves. There is no auto-approval threshold; a refund
request for even a small amount still requires approval before it is executed.

## What a refund request looks like

A refund request captures the originating payment, the amount, and the reason. Its status is
always `pending_approval` immediately after creation. Only after a human approves it does its
status change and the refund actually get processed; only then may a customer-facing message
say the refund happened.
