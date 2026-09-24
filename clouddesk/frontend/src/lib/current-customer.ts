// name: lib/current-customer.ts
// purpose: Server-side helper that resolves the authenticated customer id for the customer
//          portal (Phase 10, spec section 27). This replaces the Phase 9 demo cookie-switcher
//          placeholder: the id now comes from a verified-shape JWT issued by
//          POST /api/v1/auth/login (see app/api/auth/login/route.ts, which sets the httpOnly
//          cookie this reads). A missing, malformed, expired, or wrong-role token redirects to
//          the login page rather than silently falling back to a default customer — there is no
//          safe default once real authentication exists.
// author: CloudDesk Team
// date: 2026-09-24

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { decodeJwtPayload, isTokenExpired } from "@/lib/auth/jwt";
import { AUTH_TOKEN_COOKIE } from "@/lib/constants";

/** The logged-in customer's id, or redirects to /login if not authenticated as a customer. */
export async function getCurrentCustomerId(): Promise<string> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_TOKEN_COOKIE)?.value;
  const payload = decodeJwtPayload(token);

  if (!payload || payload.role !== "customer" || !payload.customer_id || isTokenExpired(payload)) {
    redirect("/login");
  }
  return payload.customer_id;
}
