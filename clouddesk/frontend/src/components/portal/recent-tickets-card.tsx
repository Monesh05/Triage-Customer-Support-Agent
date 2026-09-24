// name: components/portal/recent-tickets-card.tsx
// purpose: "Recent activity" card on the dashboard: the customer's most recent support tickets.
//          Shared visual style with the full ticket history list on /support.
// author: CloudDesk Team
// date: 2026-09-24

import { Inbox } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SupportTicket } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

const MAX_RECENT_TICKETS: number = 5;

export function RecentTicketsCard({ tickets }: { tickets: SupportTicket[] }) {
  const recentTickets = tickets.slice(0, MAX_RECENT_TICKETS);

  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle className="text-base">Recent activity</CardTitle>
      </CardHeader>
      <CardContent>
        {recentTickets.length === 0 ? (
          <EmptyState
            icon={Inbox}
            title="No support tickets yet"
            description="Anything you ask the AI Support team will show up here."
          />
        ) : (
          <ul className="divide-y divide-border">
            {recentTickets.map((ticket) => (
              <li key={ticket.id} className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{ticket.subject}</p>
                  <p className="text-xs text-muted-foreground">{formatDateTime(ticket.created_at)}</p>
                </div>
                <StatusBadge status={ticket.status} />
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
