// name: components/portal/billing-incident-alert.tsx
// purpose: A dedicated "billing incident" component (spec section 6) shown above the payment
//          history table when a likely duplicate charge is detected on this account — distinct
//          from a generic alert box, with the transaction references visually secondary and a
//          clear call to action into the real AI Support flow (billing disputes route through the
//          Billing Agent + human-approval workflow, not a self-service refund button).
// author: CloudDesk Team
// date: 2026-09-25

import Link from "next/link";
import { TriangleAlert } from "lucide-react";

import { Button } from "@/components/ui/button";
import { formatCurrency, formatDate } from "@/lib/format";
import type { Payment } from "@/lib/api/types";

/** Successful payments on the same subscription that were charged more than once — a real,
 * data-derived signal (not fabricated), matching the detection payments-table.tsx used before this
 * redesign split the warning into its own component. */
export function findDuplicatePayments(payments: Payment[]): Payment[] {
  const succeeded = payments.filter((p) => p.status === "succeeded");
  const bySubscription = new Map<string, Payment[]>();
  for (const payment of succeeded) {
    const group = bySubscription.get(payment.subscription_id) ?? [];
    group.push(payment);
    bySubscription.set(payment.subscription_id, group);
  }
  for (const group of bySubscription.values()) {
    if (group.length > 1) {
      return group;
    }
  }
  return [];
}

export function BillingIncidentAlert({ duplicatePayments }: { duplicatePayments: Payment[] }) {
  if (duplicatePayments.length < 2) {
    return null;
  }

  const [first, second] = duplicatePayments;

  return (
    <div className="rounded-lg border border-warning/40 bg-warning/10 px-4 py-3.5">
      <div className="flex items-start gap-3">
        <TriangleAlert className="mt-0.5 size-4.5 shrink-0 text-warning-foreground" strokeWidth={2} />
        <div className="min-w-0 flex-1 space-y-1.5">
          <p className="text-sm font-semibold text-warning-foreground">Potential duplicate charge detected</p>
          <p className="text-sm text-warning-foreground/90">
            Two successful {formatCurrency(first.amount, first.currency)} charges were recorded on{" "}
            {formatDate(first.created_at)}.
          </p>
          <p className="font-mono text-xs text-warning-foreground/60">
            {first.transaction_reference} · {second.transaction_reference}
          </p>
          <div className="pt-1">
            <Button size="sm" render={<Link href="/support">Investigate with AI Support</Link>} />
          </div>
        </div>
      </div>
    </div>
  );
}
