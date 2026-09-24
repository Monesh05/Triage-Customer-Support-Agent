---
document_id: api-authentication
title: Authenticating API Requests
category: API documentation
product: CloudDesk API
version: "1.2"
source: docs/api/authentication.md
updated_at: 2026-08-01
---

# Authenticating API Requests

Every CloudDesk API request must include an API key in the `Authorization` header:

```
Authorization: Bearer cd_live_<your_api_key>
```

## Creating an API key

API keys are created from the dashboard's "API" page. Creating a key requires the
`api_access` feature, which is included from the Pro plan upward — Free-plan customers
cannot create API keys and must upgrade first.

## Key status

Every API key has a status: `active`, `revoked`, or `expired`. Only `active` keys are
accepted on live requests. CloudDesk never displays a key's raw secret again after creation;
only its hash and metadata (status, creation date, last-used date, rate limit) are ever
shown afterward. If a key's secret is lost, it must be rotated (see "Rotating an API Key"),
not recovered.

## Common authentication errors

A request with a missing or malformed `Authorization` header returns `401 Unauthorized`.
A request with a valid but revoked or expired key also returns `401`. A `403 Forbidden`
response is different: it means the key is valid, but the request is not entitled to the
resource — most commonly because the subscription's plan entitlement doesn't match what the
customer expects (see "Diagnosing 403 API Errors").
