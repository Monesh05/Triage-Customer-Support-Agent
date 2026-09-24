// name: app/(portal)/layout.tsx
// purpose: Server layout for the customer portal route group. Resolves the authenticated
//          customer id from the signed JWT (Phase 10, spec section 27 — see
//          lib/current-customer.ts; redirects to /login if not authenticated), looks up that
//          customer's own record for display, and renders the branded portal shell around every
//          /dashboard, /billing, /usage, /api, /support page.
// author: CloudDesk Team
// date: 2026-09-24

import { PortalShell } from "@/components/portal/portal-shell";
import { getCustomer } from "@/lib/api/customers";
import { getCurrentCustomerId } from "@/lib/current-customer";

export default async function PortalLayout({ children }: { children: React.ReactNode }) {
  const customerId = await getCurrentCustomerId();
  const customer = await getCustomer(customerId);
  return <PortalShell customerEmail={customer.email}>{children}</PortalShell>;
}
