// name: lib/auth/jwt.ts
// purpose: Decode (never verify) a JWT's payload for UI purposes only — e.g. showing "logged in
//          as X" or deciding which nav/redirect to render. Signature verification is the
//          backend's job on every real API call (it always re-validates the same token via
//          Authorization: Bearer); this module must never be used to make an authorization
//          decision that matters, only a display/redirect one, since a tampered payload here can
//          at worst make the frontend render the wrong thing, never grant real access to data —
//          the backend independently rejects any tampered/invalid signature.
// author: CloudDesk Team
// date: 2026-09-24

export interface AccessTokenPayload {
  sub: string;
  role: "customer" | "staff";
  customer_id?: string;
  exp: number;
  iat: number;
}

function isAccessTokenPayload(value: unknown): value is AccessTokenPayload {
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;
  return (
    typeof record.sub === "string" &&
    (record.role === "customer" || record.role === "staff") &&
    typeof record.exp === "number"
  );
}

/** Decode a JWT's payload segment without verifying its signature. Returns null for a missing,
 * malformed, or unparseable token — callers must treat that the same as "not authenticated". */
export function decodeJwtPayload(token: string | undefined): AccessTokenPayload | null {
  if (!token) return null;
  const segments = token.split(".");
  if (segments.length !== 3) return null;
  try {
    const base64 = segments[1].replace(/-/g, "+").replace(/_/g, "/");
    const json = Buffer.from(base64, "base64").toString("utf-8");
    const parsed: unknown = JSON.parse(json);
    return isAccessTokenPayload(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

const SECONDS_TO_MILLISECONDS: number = 1000;

export function isTokenExpired(payload: AccessTokenPayload): boolean {
  return payload.exp * SECONDS_TO_MILLISECONDS <= Date.now();
}
