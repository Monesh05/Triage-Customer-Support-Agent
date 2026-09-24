// name: components/chat/ticket-history-list.tsx
// purpose: /support page's sidebar: the customer's past support tickets, so they can see history
//          alongside starting a new AI Support conversation.
// author: CloudDesk Team
// date: 2026-09-24

import { History } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SupportTicket } from "@/lib/api/types";
import { formatDate } from "@/lib/format";

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
          <ul className="max-h-[calc(100vh-16rem)] space-y-1 overflow-y-auto">
            {tickets.map((ticket) => (
              <li key={ticket.id} className="rounded-lg border border-transparent px-2.5 py-2 hover:border-border">
                <p className="truncate text-sm font-medium">{ticket.subject}</p>
                <div className="mt-1 flex items-center justify-between gap-2">
                  <span className="text-xs text-muted-foreground">{formatDate(ticket.created_at)}</span>
                  <StatusBadge status={ticket.status} className="text-[10px]" />
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
