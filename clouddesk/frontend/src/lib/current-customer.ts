// name: lib/current-customer.ts
// purpose: Server-side helper that resolves "the current customer" for the customer portal from
//          a plain cookie. This is an explicit placeholder for Phase 10's real authentication
//          (spec section 32): once a real session exists, only this function's body needs to
//          change (read the session instead of the cookie) — every page already calls it instead
//          of touching customer ids directly.
// author: CloudDesk Team
// date: 2026-09-24

import { cookies } from "next/headers";

import { CURRENT_CUSTOMER_COOKIE } from "@/lib/constants";
import { DEFAULT_DEMO_CUSTOMER_ID, DEMO_CUSTOMERS } from "@/lib/demo-customers";

/** Resolve the demo customer id to use for this request, from the `clouddesk_customer_id`
 * cookie set by <CustomerSwitcher>. Falls back to the first demo customer when unset or the
 * cookie value is not one of the known seeded ids. */
export async function getCurrentCustomerId(): Promise<string> {
  const cookieStore = await cookies();
  const value = cookieStore.get(CURRENT_CUSTOMER_COOKIE)?.value;
  const isKnownCustomer = DEMO_CUSTOMERS.some((demoCustomer) => demoCustomer.id === value);
  return isKnownCustomer && value ? value : DEFAULT_DEMO_CUSTOMER_ID;
}
