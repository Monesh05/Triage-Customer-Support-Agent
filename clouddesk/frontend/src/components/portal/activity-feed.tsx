// name: components/portal/activity-feed.tsx
// purpose: Dashboard "Recent activity" feed (spec section 5): merges the customer's own support
//          tickets with active service incidents into one reverse-chronological feed, each row
//          getting an icon, a relative-ish timestamp, a title, a short description, and a status
//          badge. Built entirely from data the dashboard already fetches (SupportTicket,
//          ServiceIncident) — no synthetic events.
// author: CloudDesk Team
// date: 2026-09-25

import { AlertTriangle, MessageCircle } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ServiceIncident, SupportTicket } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

const MAX_ACTIVITY_ITEMS: number = 6;

interface ActivityItem {
  id: string;
  timestamp: string;
  icon: typeof MessageCircle;
  title: string;
  description: string;
  status: string;
}

function buildActivity(tickets: SupportTicket[], incidents: ServiceIncident[]): ActivityItem[] {
  const ticketItems: ActivityItem[] = tickets.map((ticket) => ({
    id: `ticket-${ticket.id}`,
    timestamp: ticket.created_at,
    icon: MessageCircle,
    title: "AI Support ticket created",
    description: ticket.subject,
    status: ticket.status,
  }));

  const incidentItems: ActivityItem[] = incidents.map((incident) => ({
    id: `incident-${incident.id}`,
    timestamp: incident.started_at,
    icon: AlertTriangle,
    title: `${incident.service_name} issue detected`,
    description: incident.description,
    status: incident.status,
  }));

  return [...ticketItems, ...incidentItems]
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, MAX_ACTIVITY_ITEMS);
}

export function ActivityFeed({
  tickets,
  incidents,
}: {
  tickets: SupportTicket[];
  incidents: ServiceIncident[];
}) {
  const items = buildActivity(tickets, incidents);

  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle className="text-base">Recent activity</CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <EmptyState
            icon={MessageCircle}
            title="No recent activity"
            description="Support tickets and account events will show up here."
          />
        ) : (
          <ul className="divide-y divide-border">
            {items.map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.id} className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
                  <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-muted">
                    <Icon className="size-3.5 text-muted-foreground" strokeWidth={2} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                      <p className="text-sm font-medium">{item.title}</p>
                      <span className="text-xs text-muted-foreground">{formatDateTime(item.timestamp)}</span>
                    </div>
                    <p className="mt-0.5 truncate text-sm text-muted-foreground">{item.description}</p>
                  </div>
                  <StatusBadge status={item.status} className="mt-0.5 shrink-0" />
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
