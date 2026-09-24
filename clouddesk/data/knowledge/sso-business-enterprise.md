---
document_id: sso-business-enterprise
title: Single Sign-On (SSO) for Business and Enterprise
category: feature documentation
product: CloudDesk Platform
version: "1.0"
source: docs/features/sso.md
updated_at: 2026-04-22
---

# Single Sign-On (SSO) for Business and Enterprise

Single sign-on (SSO) lets an organization's users authenticate to CloudDesk using their
company identity provider (e.g. Okta, Azure AD, Google Workspace) instead of a separate
CloudDesk password. SSO is included on the Business and Enterprise plans (the `sso` feature
flag) and is not available on Free or Pro.

## How SSO changes login

When SSO is enabled for an organization, member accounts authenticate through the
configured identity provider's login flow; CloudDesk never sees or stores the underlying
password. MFA enforcement can still be layered on top if the identity provider itself
requires it, but CloudDesk's own MFA toggle is not used for SSO-authenticated accounts.

## Setting up SSO

SSO configuration (identity provider metadata, allowed domains) is set up by an
organization administrator from the dashboard's organization settings, not per individual
customer account. Enterprise customers with non-standard identity provider requirements
should contact their dedicated support contact rather than self-configuring.

## Downgrading away from SSO

If an organization downgrades from Business/Enterprise to a plan without the `sso` feature,
existing SSO-authenticated accounts will be unable to log in via SSO once the downgrade's
entitlement sync completes; affected users need a standard CloudDesk password set (via the
account recovery flow) before the downgrade takes effect, to avoid a lockout.
