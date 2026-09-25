// name: app/(portal)/billing/page.tsx
// purpose: Customer portal billing page (spec section 25): subscription details, payment
//          history, and invoices. Server Component.
//          2026-09-25 redesign (spec section 6): Stripe-style layout — current plan, a dedicated
//          billing-incident alert when a duplicate charge is detected, then payment history and
//          invoices as polished tables.
// author: CloudDesk Team
// date: 2026-09-25

import { BillingIncidentAlert, findDuplicatePayments } from "@/components/portal/billing-incident-alert";
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
  const duplicatePayments = findDuplicatePayments(payments);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-semibold tracking-tight">Billing</h1>
        <p className="text-sm text-muted-foreground">Your subscription, payments, and invoices.</p>
      </div>

      <PlanSummaryCard subscriptions={subscriptions} />
      <BillingIncidentAlert duplicatePayments={duplicatePayments} />
      <PaymentsTable payments={payments} />
      <InvoicesTable invoices={invoices} />
    </div>
  );
}
