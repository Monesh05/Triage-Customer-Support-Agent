// name: components/portal/plan-summary-card.tsx
// purpose: "Current plan" card shown on both the dashboard and /billing (spec section 6, modeled
//          on Stripe's billing UI): plan name/price/renewal date, a status badge, and a feature
//          checklist. There is no self-service plan-change endpoint on the backend, so "Manage
//          plan" deliberately routes to AI Support (a real, working feature) rather than being a
//          dead button that calls nothing.
// author: CloudDesk Team
// date: 2026-09-25

import Link from "next/link";
import { CheckCircle2, PackageSearch } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Subscription } from "@/lib/api/types";
import { formatCurrency, formatDate, formatEnumLabel } from "@/lib/format";

export function PlanSummaryCard({ subscriptions }: { subscriptions: Subscription[] }) {
  const activeSubscription = subscriptions.find((s) => s.status === "active") ?? subscriptions[0];

  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle className="text-base">Current plan</CardTitle>
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
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-xl font-semibold tracking-tight">{activeSubscription.plan.name}</p>
                  <StatusBadge status={activeSubscription.status} />
                </div>
                <p className="text-sm text-muted-foreground">
                  {formatCurrency(activeSubscription.plan.price_monthly)}/month · renews{" "}
                  {formatDate(activeSubscription.renewal_date)}
                </p>
              </div>
              <Button size="sm" variant="outline" render={<Link href="/support">Manage plan</Link>} />
            </div>
            <ul className="grid gap-1.5 sm:grid-cols-2">
              {activeSubscription.plan.features.map((feature) => (
                <li key={feature} className="flex items-center gap-2 text-sm text-foreground">
                  <CheckCircle2 className="size-3.5 shrink-0 text-success" />
                  {formatEnumLabel(feature)}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
