// name: components/chat/ticket-history-list.tsx
// purpose: /support page's sidebar: the customer's past support tickets, so they can see history
//          alongside starting a new AI Support conversation. Each ticket links through to its own
//          customer-facing detail page at /support/tickets/[id]. 2026-09-25 redesign (spec section
//          12): tickets now render as the shared TicketCard component instead of a bespoke list
//          item, so the same visual treatment is used everywhere a ticket is listed.
// author: CloudDesk Team
// date: 2026-09-25

import { History } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { TicketCard } from "@/components/shared/ticket-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SupportTicket } from "@/lib/api/types";

export function TicketHistoryList({ tickets }: { tickets: SupportTicket[] }) {
  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <History className="size-4" />
          Your tickets
        </CardTitle>
      </CardHeader>
      <CardContent>
        {tickets.length === 0 ? (
          <EmptyState icon={History} title="No tickets yet" description="Start a conversation to create one." />
        ) : (
          <ul className="max-h-[calc(100vh-20rem)] space-y-1 overflow-y-auto">
            {tickets.map((ticket) => (
              <li key={ticket.id}>
                <TicketCard ticket={ticket} />
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
