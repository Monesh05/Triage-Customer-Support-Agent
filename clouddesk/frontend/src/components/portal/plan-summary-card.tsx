// name: components/portal/plan-summary-card.tsx
// purpose: Dashboard card summarizing the customer's active subscription/plan.
// author: CloudDesk Team
// date: 2026-09-24

import { PackageSearch } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Subscription } from "@/lib/api/types";
import { formatCurrency, formatDate } from "@/lib/format";

export function PlanSummaryCard({ subscriptions }: { subscriptions: Subscription[] }) {
  const activeSubscription = subscriptions.find((s) => s.status === "active") ?? subscriptions[0];

  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle className="text-base">Your plan</CardTitle>
      </CardHeader>
      <CardContent>
        {!activeSubscription ? (
          <EmptyState
            icon={PackageSearch}
            title="No subscription found"
            description="This account has no billing subscription on record."
          />
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xl font-semibold">{activeSubscription.plan.name}</p>
                <p className="text-sm text-muted-foreground">
                  {formatCurrency(activeSubscription.plan.price_monthly)}/mo · renews{" "}
                  {formatDate(activeSubscription.renewal_date)}
                </p>
              </div>
              <StatusBadge status={activeSubscription.status} />
            </div>
            <div className="flex flex-wrap gap-1.5">
              {activeSubscription.plan.features.map((feature) => (
                <span
                  key={feature}
                  className="rounded-full bg-secondary px-2.5 py-1 text-xs font-medium text-secondary-foreground"
                >
                  {feature.replaceAll("_", " ")}
                </span>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
