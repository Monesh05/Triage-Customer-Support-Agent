"use client";

// name: components/console/approval-queue.tsx
// purpose: The Approval Queue's client-side list (spec section 26): wires ApprovalCard to the
//          real POST /approvals/{id}/approve|reject endpoints and surfaces the ACTUAL outcome
//          (executed, whether the paused workflow resumed, its final_response) via a toast —
//          never a fake "success" disconnected from what the backend actually did.
// author: CloudDesk Team
// date: 2026-09-24

import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import { toast } from "sonner";

import { ApprovalActorInput } from "@/components/console/approval-actor-input";
import { ApprovalCard } from "@/components/console/approval-card";
import { EmptyState } from "@/components/shared/empty-state";
import { ApiError } from "@/lib/api/client";
import { approveAction, rejectAction } from "@/lib/api/approvals";
import type { ApprovalRequest } from "@/lib/api/types";

const DEFAULT_ACTOR: string = "support_console";

function describeOutcome(executed: boolean, workflowResumed: boolean, finalResponse: string | null): string {
  const parts = [executed ? "Action executed." : "No side effect executed."];
  if (workflowResumed) {
    parts.push(finalResponse ? `Workflow resumed: "${finalResponse}"` : "Workflow resumed.");
  }
  return parts.join(" ");
}

export function ApprovalQueue({ initialApprovals }: { initialApprovals: ApprovalRequest[] }) {
  const [approvals, setApprovals] = useState(initialApprovals);
  const [actor, setActor] = useState(DEFAULT_ACTOR);
  const [processingId, setProcessingId] = useState<string | null>(null);

  async function handleDecision(approvalId: string, decide: () => Promise<{
    approval_request: ApprovalRequest;
    executed: boolean;
    workflow_resumed: boolean;
    final_response: string | null;
  }>) {
    setProcessingId(approvalId);
    try {
      const result = await decide();
      setApprovals((prev) => prev.map((a) => (a.id === approvalId ? result.approval_request : a)));
      toast.success(
        `Action ${result.approval_request.status}`,
        { description: describeOutcome(result.executed, result.workflow_resumed, result.final_response) }
      );
    } catch (cause) {
      toast.error("Decision failed", {
        description: cause instanceof ApiError ? cause.detail : "Unknown error",
      });
    } finally {
      setProcessingId(null);
    }
  }

  const pending = approvals.filter((a) => a.status === "pending");
  const decided = approvals.filter((a) => a.status !== "pending");

  return (
    <div className="space-y-6">
      <ApprovalActorInput actor={actor} onChange={setActor} />

      {pending.length === 0 && decided.length === 0 ? (
        <EmptyState
          icon={ShieldCheck}
          title="No pending approvals right now"
          description="When an agent needs a human sign-off (refunds, account unlocks), it will show up here."
        />
      ) : (
        <div className="space-y-3">
          {pending.map((approval) => (
            <ApprovalCard
              key={approval.id}
              approval={approval}
              isProcessing={processingId === approval.id}
              onApprove={() => handleDecision(approval.id, () => approveAction(approval.id, { actor }))}
              onReject={(reason) =>
                handleDecision(approval.id, () => rejectAction(approval.id, { actor, reason: reason || null }))
              }
            />
          ))}
        </div>
      )}

      {decided.length > 0 ? (
        <div className="space-y-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Decided this session
          </p>
          {decided.map((approval) => (
            <ApprovalCard
              key={approval.id}
              approval={approval}
              isProcessing={false}
              onApprove={() => Promise.resolve()}
              onReject={() => {}}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
