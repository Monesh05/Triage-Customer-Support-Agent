---
document_id: api-key-rotation
title: Rotating an API Key
category: feature documentation
product: CloudDesk API
version: "1.0"
source: docs/api/key-rotation.md
updated_at: 2026-06-10
---

# Rotating an API Key

Rotating an API key means revoking the old key and issuing a new one, without changing the
customer's plan entitlement or rate limit. Rotation is the recommended response whenever a
key secret may have been exposed (committed to a public repo, shared over an insecure
channel, etc.).

## How to rotate a key

1. Open the dashboard's "API" page and select the key to rotate.
2. Click "Rotate Key." This immediately marks the existing key `revoked` — any requests
   still using it will start failing with `401 Unauthorized`.
3. A new key is generated and shown once. Copy it immediately; CloudDesk cannot show the raw
   secret again.
4. Update the key everywhere it's configured (server environment variables, CI secrets,
   integration configs) before traffic relying on the old key is expected to resume.

## Zero-downtime rotation

For production systems that can't tolerate even a brief `401` window, create a second,
additional API key first, deploy it alongside the old one, cut traffic over, confirm the new
key is working, and only then revoke the old key manually from the API page. This avoids any
gap between revoking the old key and the new one being live.

## Rate limits after rotation

A rotated key inherits the same rate limit as the subscription's current plan; rotation
never resets or changes usage counters, which are tracked per customer, not per key.
