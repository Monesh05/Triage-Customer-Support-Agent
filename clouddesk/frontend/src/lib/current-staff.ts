// name: lib/current-staff.ts
// purpose: Server-side helper that guards the Support Console (Phase 10, spec section 27): a
//          missing, malformed, expired, or wrong-role (customer, not staff) token redirects to
//          the staff login page. Mirrors lib/current-customer.ts's shape for the customer portal.
// author: CloudDesk Team
// date: 2026-09-24

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { decodeJwtPayload, isTokenExpired } from "@/lib/auth/jwt";
import { AUTH_TOKEN_COOKIE } from "@/lib/constants";

/** Asserts the request carries a valid staff token; redirects to /support-console/login if not.
 * Returns the staff id (the JWT `sub`) for display purposes. */
export async function requireStaffSession(): Promise<string> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_TOKEN_COOKIE)?.value;
  const payload = decodeJwtPayload(token);

  if (!payload || payload.role !== "staff" || isTokenExpired(payload)) {
    redirect("/support-console/login");
  }
  return payload.sub;
}
