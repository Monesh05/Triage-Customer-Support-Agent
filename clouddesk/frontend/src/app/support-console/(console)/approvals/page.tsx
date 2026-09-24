// name: app/support-console/approvals/page.tsx
// purpose: Internal Support Console Approval Queue (spec section 26). Server Component fetches
//          the initial pending list; the interactive approve/reject flow lives in ApprovalQueue.
// author: CloudDesk Team
// date: 2026-09-24

import { ApprovalQueue } from "@/components/console/approval-queue";
import { listApprovals } from "@/lib/api/approvals";

export const dynamic = "force-dynamic";

export default async function ApprovalQueuePage() {
  const approvals = await listApprovals(false);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Approval Queue</h1>
        <p className="text-sm text-muted-foreground">
          {approvals.length} action{approvals.length === 1 ? "" : "s"} awaiting human sign-off.
        </p>
      </div>
      <ApprovalQueue initialApprovals={approvals} />
    </div>
  );
}
