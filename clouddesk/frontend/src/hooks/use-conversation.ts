"use client";

// name: hooks/use-conversation.ts
// purpose: Client-side state machine driving the AI Support chat (spec section 25): sends a
//          message via POST /conversations, then polls GET /conversations/{thread_id} until the
//          workflow reaches a terminal state (completed/escalated/failed) or pauses for human
//          approval. Kept separate from the chat UI components so ChatPanel stays a thin
//          presentational layer over this hook.
// author: CloudDesk Team
// date: 2026-09-24

import { useCallback, useEffect, useRef, useState } from "react";

import { getConversationStatus, startConversation } from "@/lib/api/conversations";
import { ApiError } from "@/lib/api/client";
import type { ConversationStatusValue, ConversationStep } from "@/lib/api/types";
import { CONVERSATION_MAX_POLL_ATTEMPTS, CONVERSATION_POLL_INTERVAL_MS } from "@/lib/constants";

export type ChatRole = "customer" | "assistant" | "system";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  text: string;
}

const CALM_FAILURE_MESSAGE: string =
  "Something went wrong while working on your request. Please try rephrasing, or try again in a moment.";
const AWAITING_APPROVAL_MESSAGE: string =
  "Your request has been sent for a quick internal review — we'll update you here once it's approved.";
const POLL_TIMEOUT_MESSAGE: string =
  "This is taking longer than expected. Your request is still being reviewed — check back shortly.";

/** Decide whether this poll result should end the conversation and, if so, what to say. A run
 * is treated as done once the backend has a `final_response` ready — even if `status` is still
 * "awaiting_approval" (observed in practice: the workflow can finish drafting its answer and
 * resume past a decided approval while the conversation record's status field lags behind) —
 * rather than only trusting the terminal status values, so the customer sees their answer as
 * soon as it exists instead of waiting out the full poll timeout. */
function terminalMessageFor(status: ConversationStatusValue, finalResponse: string | null): string | null {
  if (status === "failed") {
    return CALM_FAILURE_MESSAGE;
  }
  if (finalResponse !== null) {
    return finalResponse;
  }
  if (status === "completed" || status === "escalated") {
    return "Your request has been handled.";
  }
  return null;
}

export function useConversation(customerId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [steps, setSteps] = useState<ConversationStep[]>([]);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hasAnnouncedApproval = useRef(false);
  const hasFinished = useRef(false);
  const pollAttempts = useRef(0);
  const historyRef = useRef<string[]>([]);
  const activeIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (activeIntervalRef.current !== null) {
        clearInterval(activeIntervalRef.current);
      }
    };
  }, []);

  const appendMessage = useCallback((role: ChatRole, text: string) => {
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role, text }]);
  }, []);

  const pollConversation = useCallback(
    (threadId: string) => {
      const interval = setInterval(async () => {
        // setInterval fires on a fixed clock regardless of whether the previous tick's request
        // is still in flight, so a slow poll (e.g. cross-region to the backend) can leave two
        // ticks racing to append the same terminal message before either reaches clearInterval
        // below. hasFinished is a synchronous guard against that: only the first tick to observe
        // a terminal result may act on it.
        if (hasFinished.current) {
          return;
        }
        pollAttempts.current += 1;
        try {
          const status = await getConversationStatus(threadId);
          if (hasFinished.current) {
            return;
          }
          setSteps(status.steps);

          if (status.status === "awaiting_approval" && !hasAnnouncedApproval.current) {
            hasAnnouncedApproval.current = true;
            appendMessage("system", AWAITING_APPROVAL_MESSAGE);
          }

          const terminalMessage = terminalMessageFor(status.status, status.final_response);
          const hasTimedOut = pollAttempts.current >= CONVERSATION_MAX_POLL_ATTEMPTS;
          if (terminalMessage !== null || hasTimedOut) {
            hasFinished.current = true;
            clearInterval(interval);
            setIsBusy(false);
            setSteps([]);
            const message = terminalMessage ?? POLL_TIMEOUT_MESSAGE;
            appendMessage("assistant", message);
            historyRef.current.push(message);
          }
        } catch (cause) {
          if (hasFinished.current) {
            return;
          }
          hasFinished.current = true;
          clearInterval(interval);
          setIsBusy(false);
          setError(cause instanceof ApiError ? cause.detail : "Lost connection while checking status.");
        }
      }, CONVERSATION_POLL_INTERVAL_MS);
      activeIntervalRef.current = interval;
    },
    [appendMessage]
  );

  const sendMessage = useCallback(
    async (text: string) => {
      setError(null);
      hasAnnouncedApproval.current = false;
      hasFinished.current = false;
      pollAttempts.current = 0;
      appendMessage("customer", text);
      historyRef.current.push(text);
      setIsBusy(true);
      setSteps([{ step: "Understanding request", status: "in_progress" }]);

      try {
        const { thread_id: threadId } = await startConversation({
          customer_id: customerId,
          message: text,
          conversation_history: historyRef.current.slice(0, -1),
        });
        pollConversation(threadId);
      } catch (cause) {
        setIsBusy(false);
        setSteps([]);
        setError(cause instanceof ApiError ? cause.detail : "Could not start the conversation.");
      }
    },
    [appendMessage, customerId, pollConversation]
  );

  return { messages, steps, isBusy, error, sendMessage };
}
