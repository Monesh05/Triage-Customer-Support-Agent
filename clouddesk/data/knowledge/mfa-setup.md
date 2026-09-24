---
document_id: mfa-setup
title: How Multi-Factor Authentication (MFA) Works
category: feature documentation
product: CloudDesk Platform
version: "1.0"
source: docs/features/mfa.md
updated_at: 2026-05-18
---

# How Multi-Factor Authentication (MFA) Works

Multi-factor authentication (MFA) adds a second verification step to account login, beyond
a password. CloudDesk supports time-based one-time passcode (TOTP) authenticator apps (e.g.
Google Authenticator, Authy, 1Password).

## Enabling MFA

MFA is enabled per account from the dashboard's account security settings. Once enabled, the
account record's `mfa_enabled` flag is set to true, and every subsequent login requires both
the account password and a valid TOTP code. MFA is available on every plan, including Free —
it is a security control, not a paid feature.

## What MFA does not protect against

MFA protects the login step. It does not by itself protect API keys (which authenticate API
requests independently of a human login session) or prevent account lockout from repeated
failed login attempts — both are separate controls. See "Account Recovery After Lockout" for
what happens when an account is locked.

## Losing access to your authenticator

If a customer loses access to their MFA device, they cannot self-service disable MFA from
the login screen for security reasons. This requires identity verification through account
recovery, the same process used for locked accounts. CloudDesk support will never disable
MFA on request alone without verifying identity first — doing so would defeat the purpose of
the control.
