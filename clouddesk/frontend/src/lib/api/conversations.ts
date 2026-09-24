// name: lib/api/conversations.ts
// purpose: Typed client functions for the Phase 9 customer-facing chat API (spec section 25):
//          starting a support conversation and polling its live status.
// author: CloudDesk Team
// date: 2026-09-24

import { apiRequest } from "@/lib/api/client";
import type {
  ConversationStartRequest,
  ConversationStartResponse,
  ConversationStatus,
} from "@/lib/api/types";

export function startConversation(
  payload: ConversationStartRequest
): Promise<ConversationStartResponse> {
  return apiRequest<ConversationStartResponse>("/conversations", {
    method: "POST",
    body: payload,
  });
}

export function getConversationStatus(threadId: string): Promise<ConversationStatus> {
  return apiRequest<ConversationStatus>(`/conversations/${threadId}`);
}
