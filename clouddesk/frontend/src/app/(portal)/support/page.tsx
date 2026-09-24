// name: app/(portal)/support/page.tsx
// purpose: Customer portal AI Support page (spec section 25) — the flagship chat feature, plus a
//          ticket-history sidebar. The chat itself is a Client Component (ChatPanel); the ticket
//          history is fetched server-side.
// author: CloudDesk Team
// date: 2026-09-24

import { ChatPanel } from "@/components/chat/chat-panel";
import { TicketHistoryList } from "@/components/chat/ticket-history-list";
import { getCustomerTickets } from "@/lib/api/customers";
import { getCurrentCustomerId } from "@/lib/current-customer";

export const dynamic = "force-dynamic";

export default async function SupportPage() {
  const customerId = await getCurrentCustomerId();
  const tickets = await getCustomerTickets(customerId);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">AI Support</h1>
        <p className="text-sm text-muted-foreground">
          Chat with the CloudDesk AI Support team — billing, account, and technical issues, all in
          one place.
        </p>
      </div>
      <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
        <ChatPanel customerId={customerId} />
        <div className="hidden lg:block">
          <TicketHistoryList tickets={tickets} />
        </div>
      </div>
    </div>
  );
}
