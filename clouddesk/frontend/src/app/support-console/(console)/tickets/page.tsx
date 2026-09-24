// name: app/support-console/tickets/page.tsx
// purpose: Internal Support Console Tickets list (spec section 26). Server Component.
// author: CloudDesk Team
// date: 2026-09-24

import { TicketsTable } from "@/components/console/tickets-table";
import { listAllTickets } from "@/lib/api/tickets";

export const dynamic = "force-dynamic";

export default async function ConsoleTicketsPage() {
  const tickets = await listAllTickets();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Tickets</h1>
        <p className="text-sm text-muted-foreground">
          {tickets.length} most recent support tickets across all customers.
        </p>
      </div>
      <TicketsTable tickets={tickets} />
    </div>
  );
}
