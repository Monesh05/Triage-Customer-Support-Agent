// name: components/console/tickets-table.tsx
// purpose: Support Console Tickets list (spec section 26): ticket, customer, priority, status.
//          "Intent" is shown from the ticket subject (the backend has no separate stored intent
//          field on SupportTicket — see app/models/ticket.py — so the subject line, which the
//          Triage Agent writes descriptively, is the closest honest proxy without inventing a
//          field the API does not return).
// author: CloudDesk Team
// date: 2026-09-24

import Link from "next/link";
import { Inbox } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { SupportTicket } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

export function TicketsTable({ tickets }: { tickets: SupportTicket[] }) {
  if (tickets.length === 0) {
    return (
      <Card className="border-border/70">
        <CardContent className="pt-6">
          <EmptyState icon={Inbox} title="No tickets" description="No support tickets have been created yet." />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border/70">
      <CardContent className="px-0 pt-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Ticket</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Updated</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tickets.map((ticket) => (
              <TableRow key={ticket.id}>
                <TableCell className="max-w-xs">
                  <Link
                    href={`/support-console/tickets/${ticket.id}`}
                    className="line-clamp-1 font-medium text-primary hover:underline"
                  >
                    {ticket.subject}
                  </Link>
                </TableCell>
                <TableCell className="font-mono text-xs text-muted-foreground">
                  {ticket.customer_id.slice(0, 8)}
                </TableCell>
                <TableCell>
                  <StatusBadge status={ticket.priority} />
                </TableCell>
                <TableCell>
                  <StatusBadge status={ticket.status} />
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {formatDateTime(ticket.updated_at)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
