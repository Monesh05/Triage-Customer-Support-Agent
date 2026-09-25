// name: components/shared/ticket-card.tsx
// purpose: Reusable ticket card (spec sections 12 and 15): title, category (subject's first
//          clause is too unreliable to parse, so we surface the ticket's priority as a stand-in
//          "at a glance" tag alongside its status) and created date. Used by the AI Support ticket
//          history sidebar; the customer ticket detail page's own header stays a plain page title
//          since it does not need to link anywhere.
// author: CloudDesk Team
// date: 2026-09-25

import Link from "next/link";

import { StatusBadge } from "@/components/shared/status-badge";
import type { SupportTicket } from "@/lib/api/types";
import { formatDate, formatEnumLabel } from "@/lib/format";

export function TicketCard({ ticket }: { ticket: SupportTicket }) {
  return (
    <Link
      href={`/support/tickets/${ticket.id}`}
      className="block rounded-lg border border-transparent px-3 py-2.5 transition-colors hover:border-border hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
    >
      <p className="truncate text-sm font-medium leading-snug">{ticket.subject}</p>
      <div className="mt-1.5 flex items-center justify-between gap-2">
        <span className="text-xs text-muted-foreground">
          {formatEnumLabel(ticket.priority)} · {formatDate(ticket.created_at)}
        </span>
        <StatusBadge status={ticket.status} className="shrink-0 text-[10px]" />
      </div>
    </Link>
  );
}
