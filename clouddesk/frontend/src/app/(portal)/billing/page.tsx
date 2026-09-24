// name: app/(portal)/billing/page.tsx
// purpose: Customer portal billing page (spec section 25): subscription details, payment
//          history, and invoices. Server Component.
// author: CloudDesk Team
// date: 2026-09-24

import { InvoicesTable } from "@/components/portal/invoices-table";
import { PaymentsTable } from "@/components/portal/payments-table";
import { PlanSummaryCard } from "@/components/portal/plan-summary-card";
import { getInvoices, getPayments, getSubscriptions } from "@/lib/api/billing";
import { getCurrentCustomerId } from "@/lib/current-customer";

export const dynamic = "force-dynamic";

export default async function BillingPage() {
  const customerId = await getCurrentCustomerId();
  const [subscriptions, payments, invoices] = await Promise.all([
    getSubscriptions(customerId),
    getPayments(customerId),
    getInvoices(customerId),
  ]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Billing</h1>
        <p className="text-sm text-muted-foreground">Your subscription, payments, and invoices.</p>
      </div>

      <PlanSummaryCard subscriptions={subscriptions} />
      <PaymentsTable payments={payments} />
      <InvoicesTable invoices={invoices} />
    </div>
  );
}
