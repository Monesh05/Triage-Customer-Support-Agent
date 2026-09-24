// name: app/(portal)/layout.tsx
// purpose: Server layout for the customer portal route group. Resolves the current demo
//          customer id from the request cookie (lib/current-customer.ts) and renders the
//          branded portal shell around every /dashboard, /billing, /usage, /api, /support page.
// author: CloudDesk Team
// date: 2026-09-24

import { PortalShell } from "@/components/portal/portal-shell";
import { getCurrentCustomerId } from "@/lib/current-customer";

export default async function PortalLayout({ children }: { children: React.ReactNode }) {
  const customerId = await getCurrentCustomerId();
  return <PortalShell customerId={customerId}>{children}</PortalShell>;
}
