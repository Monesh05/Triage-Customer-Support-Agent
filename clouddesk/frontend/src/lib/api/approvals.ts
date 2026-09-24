// name: lib/api/approvals.ts
// purpose: Typed client functions for the human-in-the-loop Approval Queue (spec sections 22, 26).
// author: CloudDesk Team
// date: 2026-09-24

import { apiRequest } from "@/lib/api/client";
import type {
  ApprovalDecisionRequest,
  ApprovalDecisionResponse,
  ApprovalRequest,
} from "@/lib/api/types";

export function listApprovals(includeDecided: boolean = false): Promise<ApprovalRequest[]> {
  return apiRequest<ApprovalRequest[]>(`/approvals?include_decided=${includeDecided}`);
}

export function approveAction(
  actionId: string,
  payload: ApprovalDecisionRequest
): Promise<ApprovalDecisionResponse> {
  return apiRequest<ApprovalDecisionResponse>(`/approvals/${actionId}/approve`, {
    method: "POST",
    body: payload,
  });
}

export function rejectAction(
  actionId: string,
  payload: ApprovalDecisionRequest
): Promise<ApprovalDecisionResponse> {
  return apiRequest<ApprovalDecisionResponse>(`/approvals/${actionId}/reject`, {
    method: "POST",
    body: payload,
  });
}
