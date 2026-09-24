---
document_id: account-recovery
title: Account Recovery After Lockout
category: account recovery
product: CloudDesk Platform
version: "1.0"
source: docs/policy/account-recovery.md
updated_at: 2026-05-30
---

# Account Recovery After Lockout

CloudDesk locks an account after 5 consecutive failed login attempts as a brute-force
protection. Recovering access requires an explicit unlock, not simply waiting or retrying.

## Identity verification is mandatory

Before any account is unlocked, CloudDesk requires identity verification. This exists
specifically so that an attacker who triggered the lockout by guessing passwords cannot then
also request the unlock and gain access. Support agents (human or AI) must never unlock an
account based solely on a chat message claiming to be the account owner.

## The unlock process

Once identity is verified through the appropriate channel, an unlock is performed via
`POST /api/v1/accounts/unlock`, which resets the account's failed-login counter and restores
login access. This is a sensitive action and, like refunds, is logged in the audit trail.

## MFA device loss is handled the same way

Losing access to an MFA authenticator app is treated as an account-recovery case, not a
simple "disable MFA" request — the same identity-verification requirement applies, since
disabling MFA without verification would undermine the protection MFA exists to provide.

## Recovery does not change plan or billing

Account recovery only restores login access. It has no effect on a customer's subscription,
plan, or entitlement — those are governed entirely separately (see the plan-upgrade
entitlement-sync documentation).
