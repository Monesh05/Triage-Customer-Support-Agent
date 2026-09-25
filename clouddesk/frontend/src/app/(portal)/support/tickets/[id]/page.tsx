// name: app/(portal)/support/tickets/[id]/page.tsx
// purpose: Customer-facing ticket detail page (post-launch, 2026-09-25): the gap this fix closes
//          was that the /support page's "Your tickets" sidebar showed a status badge that looked
//          like an "Open" button but did nothing when clicked, with no customer-facing detail page
//          at all (only staff had one, at /support-console/tickets/[id]). Shows the original
//          request, current status, and the same customer-safe outcome text the chat itself showed
//          (GET /tickets/{id}/summary) — never the staff-only raw agent trace
//          (GET /tickets/{id}/trace), which is deliberately not fetched here. Server Component,
//          following the same data-fetching convention as every other portal route.
// author: CloudDesk Team
// date: 2026-09-25

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { CloseTicketButton } from "@/components/chat/close-ticket-button";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getTicket, getTicketSummary } from "@/lib/api/tickets";
import { formatDateTime } from "@/lib/format";

export const dynamic = "force-dynamic";

const CLOSED_STATUS = "closed";

export default async function TicketDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [ticket, summary] = await Promise.all([getTicket(id), getTicketSummary(id)]);
  const isClosed = ticket.status === CLOSED_STATUS;

  return (
    <div className="space-y-4">
      <Link
        href="/support"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" />
        Back to support
      </Link>

      <Card className="border-border/70">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle className="text-lg">{ticket.subject}</CardTitle>
              <p className="mt-1 text-xs text-muted-foreground">
                Opened {formatDateTime(ticket.created_at)}
              </p>
            </div>
            <StatusBadge status={ticket.status} />
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Your message</p>
            <p className="mt-1 whitespace-pre-wrap text-sm">{ticket.description}</p>
          </div>

          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {summary.escalated ? "Escalation" : "Resolution"}
            </p>
            <p className="mt-1 text-sm">
              {summary.resolution_message ??
                "We're still working on this ticket. Check back soon for an update."}
            </p>
          </div>

          {!isClosed ? (
            <div className="flex justify-end pt-2">
              <CloseTicketButton ticketId={ticket.id} />
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
