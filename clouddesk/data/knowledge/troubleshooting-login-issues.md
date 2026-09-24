---
document_id: troubleshooting-login-issues
title: Troubleshooting Login Failures and Lockouts
category: troubleshooting
product: CloudDesk Platform
version: "1.0"
source: docs/troubleshooting/login-issues.md
updated_at: 2026-07-02
---

# Troubleshooting Login Failures and Lockouts

CloudDesk locks an account after 5 consecutive failed login attempts, to protect against
password-guessing attacks. Once locked, further login attempts are rejected regardless of
whether the correct password is eventually entered — the account must be explicitly
unlocked.

## Confirming a lockout

An account's `failed_login_attempts` count and `status` field indicate whether it is
currently locked. A customer reporting "my password isn't working" after several failed
tries is very likely locked out rather than experiencing a password-reset problem — these
require different fixes.

## Unlocking an account

Unlocking a locked account requires identity verification; it is never done purely on the
customer's say-so through chat, since an attacker who has been guessing passwords could
otherwise unlock the account themselves. Once identity is verified, an unlock can be
performed via `POST /api/v1/accounts/unlock`. This resets `failed_login_attempts` to zero
and restores login access; it does not disable MFA if MFA was already enabled.

## When it isn't a lockout

If `failed_login_attempts` is low and the account is not locked, but login still fails, check
for an active authentication-related service incident before assuming a customer-specific
account issue — intermittent login failures affecting many customers at once are usually an
incident, not individual account problems.
