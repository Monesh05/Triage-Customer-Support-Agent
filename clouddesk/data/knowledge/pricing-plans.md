---
document_id: pricing-plans
title: CloudDesk Pricing Plans
category: pricing
product: CloudDesk Platform
version: "1.0"
source: docs/pricing/plans.md
updated_at: 2026-07-15
---

# CloudDesk Pricing Plans

CloudDesk offers four subscription plans: Free, Pro, Business, and Enterprise. Every plan
includes the core dashboard, API access, and usage analytics; higher plans add a larger API
rate limit and additional features.

## Free — $0/month

The Free plan includes a 1,000 requests/month API rate limit and community support (forum
and documentation only, no direct support channel). It is intended for evaluation and small
personal projects, not production workloads.

## Pro — $49/month

The Pro plan includes a 50,000 requests/month API rate limit, community support, priority
email support, and full API access (the `api_access` feature flag, which unlocks
programmatic API key creation). Pro is CloudDesk's most popular plan for small production
teams.

## Business — $199/month

The Business plan includes a 250,000 requests/month API rate limit and everything in Pro,
plus single sign-on (SSO) and audit logs — an immutable record of sensitive account and
billing actions, useful for internal compliance reviews.

## Enterprise — $999/month

The Enterprise plan includes a 2,000,000 requests/month API rate limit and everything in
Business, plus a dedicated support contact and custom contract terms (custom rate limits,
custom data retention, and negotiated SLAs are handled outside the standard plan catalog).

## Changing plans

Upgrading or downgrading a plan takes effect on the subscription immediately, but a
customer's actual API entitlement (the rate limit and feature flags enforced on live
traffic) is synced from the new plan asynchronously. See "How Plan Upgrades Sync to Your API
Entitlement" for what to expect and how to force a refresh if it's taking too long.
