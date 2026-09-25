// name: app/(portal)/dashboard/page.tsx
// purpose: Customer portal dashboard (spec section 25): subscription/plan summary, quick stats,
//          recent activity, and account health. A Server Component — all data is fetched
//          server-side for the current authenticated customer before first paint.
//          2026-09-25 redesign (spec sections 3-5): a structured welcome header, a compact account
//          health/incident summary in place of the old large warning banner, four metric cards
//          (API usage, current plan, account status, next invoice), and a merged tickets+incidents
//          "Recent activity" feed. No new endpoints — every value below already came from the API
//          calls this page made before the redesign.
// author: CloudDesk Team
// date: 2026-09-25

import { Activity, CalendarClock, Layers, ShieldCheck } from "lucide-react";

import { ActivityFeed } from "@/components/portal/activity-feed";
import { IncidentBanner } from "@/components/portal/incident-banner";
import { PlanSummaryCard } from "@/components/portal/plan-summary-card";
import { StatCard } from "@/components/portal/stat-card";
import { getAccount, getIncidents, getInvoices, getSubscriptions, getUsage } from "@/lib/api/billing";
import { getCustomer, getCustomerTickets } from "@/lib/api/customers";
import { getCurrentCustomerId } from "@/lib/current-customer";
import { formatCurrency, formatDate } from "@/lib/format";

export const dynamic = "force-dynamic";

function findNextInvoice(invoices: Awaited<ReturnType<typeof getInvoices>>) {
  return invoices
    .filter((invoice) => invoice.status === "open" || invoice.status === "overdue")
    .sort((a, b) => new Date(a.due_at).getTime() - new Date(b.due_at).getTime())[0];
}

export default async function DashboardPage() {
  const customerId = await getCurrentCustomerId();
  const [customer, subscriptions, usageRecords, invoices, account, tickets, incidents] =
    await Promise.all([
      getCustomer(customerId),
      getSubscriptions(customerId),
      getUsage(customerId),
      getInvoices(customerId),
      getAccount(customerId),
      getCustomerTickets(customerId),
      getIncidents(),
    ]);

  const latestUsage = [...usageRecords].sort(
    (a, b) => new Date(b.period_start).getTime() - new Date(a.period_start).getTime()
  )[0];
  const activeSubscription = subscriptions.find((s) => s.status === "active") ?? subscriptions[0];
  const nextInvoice = findNextInvoice(invoices);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-semibold tracking-tight">Welcome back, {customer.name}</h1>
        <p className="text-sm text-muted-foreground">Here&apos;s what&apos;s happening with your account.</p>
      </div>

      <IncidentBanner incidents={incidents} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="API usage"
          value={latestUsage ? latestUsage.api_calls.toLocaleString() : "0"}
          hint={
            activeSubscription
              ? `of ${activeSubscription.plan.api_rate_limit.toLocaleString()} this period`
              : undefined
          }
          icon={Activity}
        />
        <StatCard
          label="Current plan"
          value={activeSubscription ? activeSubscription.plan.name : "None"}
          hint={activeSubscription ? `${formatCurrency(activeSubscription.plan.price_monthly)}/month` : undefined}
          icon={Layers}
        />
        <StatCard
          label="Account status"
          value={account.status === "active" ? "Active" : account.status}
          hint={account.status === "active" ? "Healthy account" : undefined}
          icon={ShieldCheck}
          tone={account.status === "active" ? "default" : "danger"}
        />
        <StatCard
          label="Next invoice"
          value={nextInvoice ? formatDate(nextInvoice.due_at) : "None due"}
          hint={nextInvoice ? formatCurrency(nextInvoice.amount) : undefined}
          icon={CalendarClock}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <PlanSummaryCard subscriptions={subscriptions} />
        <ActivityFeed tickets={tickets} incidents={incidents} />
      </div>
    </div>
  );
}
