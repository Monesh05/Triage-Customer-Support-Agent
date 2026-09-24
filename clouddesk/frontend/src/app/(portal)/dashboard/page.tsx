// name: app/(portal)/dashboard/page.tsx
// purpose: Customer portal dashboard (spec section 25): subscription/plan summary, quick stats,
//          recent activity, and an active-incident banner. A Server Component — all data is
//          fetched server-side for the current demo customer before first paint.
// author: CloudDesk Team
// date: 2026-09-24

import { Activity, CalendarClock, ShieldCheck } from "lucide-react";

import { IncidentBanner } from "@/components/portal/incident-banner";
import { PlanSummaryCard } from "@/components/portal/plan-summary-card";
import { RecentTicketsCard } from "@/components/portal/recent-tickets-card";
import { StatCard } from "@/components/portal/stat-card";
import { getAccount, getIncidents, getInvoices, getSubscriptions, getUsage } from "@/lib/api/billing";
import { getCustomer, getCustomerTickets } from "@/lib/api/customers";
import { getCurrentCustomerId } from "@/lib/current-customer";
import { formatDate } from "@/lib/format";

export const dynamic = "force-dynamic";

function findNextInvoiceDate(invoices: Awaited<ReturnType<typeof getInvoices>>): string {
  const upcoming = invoices
    .filter((invoice) => invoice.status === "open" || invoice.status === "overdue")
    .sort((a, b) => new Date(a.due_at).getTime() - new Date(b.due_at).getTime());
  return upcoming[0] ? formatDate(upcoming[0].due_at) : "No upcoming invoice";
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Welcome back, {customer.name}</h1>
        <p className="text-sm text-muted-foreground">Here&apos;s what&apos;s happening with your account.</p>
      </div>

      <IncidentBanner incidents={incidents} />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="API calls this period"
          value={latestUsage ? latestUsage.api_calls.toLocaleString() : "0"}
          hint={
            subscriptions[0]?.plan
              ? `of ${subscriptions[0].plan.api_rate_limit.toLocaleString()} limit`
              : undefined
          }
          icon={Activity}
        />
        <StatCard label="Next invoice" value={findNextInvoiceDate(invoices)} icon={CalendarClock} />
        <StatCard
          label="Account status"
          value={account.status === "active" ? "Active" : account.status}
          icon={ShieldCheck}
          tone={account.status === "active" ? "default" : "danger"}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <PlanSummaryCard subscriptions={subscriptions} />
        <RecentTicketsCard tickets={tickets} />
      </div>
    </div>
  );
}
