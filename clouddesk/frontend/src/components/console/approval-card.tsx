"use client";

// name: components/console/approval-card.tsx
// purpose: One Approval Queue item (spec section 26's "Refund $49 / Reason / Evidence /
//          [Approve] [Reject]" example): shows the action, amount, and raw payload as evidence,
//          with Approve/Reject controls. A reject asks for an optional reason via a small dialog.
// author: CloudDesk Team
// date: 2026-09-24

import { useState } from "react";
import { Check, Loader2, X } from "lucide-react";

import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import type { ApprovalRequest } from "@/lib/api/types";
import { formatCurrency, formatDateTime } from "@/lib/format";

export function ApprovalCard({
  approval,
  isProcessing,
  onApprove,
  onReject,
}: {
  approval: ApprovalRequest;
  isProcessing: boolean;
  onApprove: () => void;
  onReject: (reason: string) => void;
}) {
  const [rejectReason, setRejectReason] = useState("");
  const [isRejectDialogOpen, setIsRejectDialogOpen] = useState(false);

  return (
    <Card className="border-border/70">
      <CardContent className="space-y-3 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-medium">
              {approval.action_description}
              {approval.amount !== null ? ` — ${formatCurrency(approval.amount)}` : ""}
            </p>
            <p className="text-xs text-muted-foreground">
              {approval.agent_name} agent · thread {approval.thread_id.slice(0, 8)} ·{" "}
              {formatDateTime(approval.created_at)}
            </p>
          </div>
          <StatusBadge status={approval.status} />
        </div>

        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer select-none">Evidence / payload</summary>
          <pre className="mt-1.5 overflow-x-auto rounded-lg bg-muted/70 p-2">
            {JSON.stringify(approval.payload, null, 2)}
          </pre>
        </details>

        {approval.status === "pending" ? (
          <div className="flex justify-end gap-2 pt-1">
            <Dialog open={isRejectDialogOpen} onOpenChange={setIsRejectDialogOpen}>
              <DialogTrigger
                render={
                  <Button size="sm" variant="outline" disabled={isProcessing} className="gap-1.5">
                    <X className="size-3.5" />
                    Reject
                  </Button>
                }
              />
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Reject this action?</DialogTitle>
                </DialogHeader>
                <Textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Optional reason for rejecting..."
                  rows={3}
                />
                <DialogFooter>
                  <Button
                    variant="destructive"
                    onClick={() => {
                      setIsRejectDialogOpen(false);
                      onReject(rejectReason);
                    }}
                  >
                    Confirm reject
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
            <Button size="sm" onClick={onApprove} disabled={isProcessing} className="gap-1.5">
              {isProcessing ? <Loader2 className="size-3.5 animate-spin" /> : <Check className="size-3.5" />}
              Approve
            </Button>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            Decided by {approval.decided_by ?? "unknown"} at{" "}
            {approval.decided_at ? formatDateTime(approval.decided_at) : "unknown time"}
            {approval.rejection_reason ? ` — "${approval.rejection_reason}"` : ""}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
