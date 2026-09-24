// name: app/(portal)/usage/page.tsx
// purpose: Customer portal usage page (spec section 25): API usage against plan limits. Server
//          Component.
// author: CloudDesk Team
// date: 2026-09-24

import { UsageOverview } from "@/components/portal/usage-overview";
import { getSubscriptions, getUsage } from "@/lib/api/billing";
import { getCurrentCustomerId } from "@/lib/current-customer";

export const dynamic = "force-dynamic";

const FALLBACK_RATE_LIMIT: number = 1000;

export default async function UsagePage() {
  const customerId = await getCurrentCustomerId();
  const [usageRecords, subscriptions] = await Promise.all([
    getUsage(customerId),
    getSubscriptions(customerId),
  ]);

  const apiRateLimit =
    subscriptions.find((s) => s.status === "active")?.entitlement?.granted_api_rate_limit ??
    subscriptions[0]?.plan.api_rate_limit ??
    FALLBACK_RATE_LIMIT;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Usage</h1>
        <p className="text-sm text-muted-foreground">API usage against your plan&apos;s limits.</p>
      </div>
      <UsageOverview usageRecords={usageRecords} apiRateLimit={apiRateLimit} />
    </div>
  );
}
