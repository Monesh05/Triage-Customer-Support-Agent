// name: app/(portal)/support/page.tsx
// purpose: Customer portal AI Support page (spec section 25) — the flagship chat feature, a
//          ticket-history sidebar, and (2026-09-25 redesign, spec sections 9-10) a context panel
//          demonstrating the agent's real access to this customer's account/billing/usage data.
//          The chat itself is a Client Component (ChatPanel); everything else is fetched
//          server-side. No new endpoints — account/subscriptions/usage were already available via
//          lib/api/billing.ts, just not previously fetched on this page.
// author: CloudDesk Team
// date: 2026-09-25

import { ChatPanel } from "@/components/chat/chat-panel";
import { MobileContextTrigger } from "@/components/chat/mobile-context-trigger";
import { SupportContextPanel } from "@/components/chat/support-context-panel";
import { TicketHistoryList } from "@/components/chat/ticket-history-list";
import { getAccount, getSubscriptions, getUsage } from "@/lib/api/billing";
import { getCustomer, getCustomerTickets } from "@/lib/api/customers";
import { getCurrentCustomerId } from "@/lib/current-customer";

export const dynamic = "force-dynamic";

export default async function SupportPage() {
  const customerId = await getCurrentCustomerId();
  const [customer, tickets, account, subscriptions, usageRecords] = await Promise.all([
    getCustomer(customerId),
    getCustomerTickets(customerId),
    getAccount(customerId),
    getSubscriptions(customerId),
    getUsage(customerId),
  ]);

  const activeSubscription = subscriptions.find((s) => s.status === "active") ?? subscriptions[0];
  const latestUsage = [...usageRecords].sort(
    (a, b) => new Date(b.period_start).getTime() - new Date(a.period_start).getTime()
  )[0];

  const contextPanel = (
    <SupportContextPanel
      customerEmail={customer.email}
      account={account}
      subscription={activeSubscription}
      latestUsage={latestUsage}
      tickets={tickets}
    />
  );

  return (
    <div className="flex h-[calc(100vh-6.5rem)] flex-col gap-4">
      <div>
        <h1 className="text-[28px] font-semibold tracking-tight">AI Support</h1>
        <p className="text-sm text-muted-foreground">
          AI-powered support for billing, account, and technical issues.
        </p>
      </div>

      <MobileContextTrigger>{contextPanel}</MobileContextTrigger>

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[1fr_20rem]">
        <div className="min-h-0">
          <ChatPanel customerId={customerId} />
        </div>
        <div className="hidden min-h-0 flex-col gap-4 overflow-y-auto lg:flex">
          {contextPanel}
          <TicketHistoryList tickets={tickets} />
        </div>
      </div>
    </div>
  );
}
