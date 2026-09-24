// name: components/console/ticket-approval-status.tsx
// purpose: Ticket Detail's "pending approval" section (spec section 26): any human-in-the-loop
//          approval requests tied to this ticket's thread, with a link to the full Approval Queue
//          to actually decide them.
// author: CloudDesk Team
// date: 2026-09-24

import Link from "next/link";

import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ApprovalRequest } from "@/lib/api/types";
import { formatCurrency, formatDateTime } from "@/lib/format";

export function TicketApprovalStatus({ approvals }: { approvals: ApprovalRequest[] }) {
  if (approvals.length === 0) {
    return null;
  }

  return (
    <Card className="border-warning/40 bg-warning/5">
      <CardHeader>
        <CardTitle className="text-base">Approval requests</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {approvals.map((approval) => (
          <div key={approval.id} className="flex items-start justify-between gap-3 text-sm">
            <div>
              <p className="font-medium">
                {approval.action_description}
                {approval.amount ? ` (${formatCurrency(approval.amount)})` : ""}
              </p>
              <p className="text-xs text-muted-foreground">
                Requested {formatDateTime(approval.created_at)}
                {approval.decided_by ? ` · decided by ${approval.decided_by}` : ""}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge status={approval.status} />
              {approval.status === "pending" ? (
                <Link href="/support-console/approvals" className="text-xs text-primary hover:underline">
                  Review
                </Link>
              ) : null}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
