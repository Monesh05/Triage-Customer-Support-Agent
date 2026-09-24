"use client";

// name: components/chat/chat-message-list.tsx
// purpose: Scrollable chat transcript: message bubbles plus the live progress panel while a
//          request is in flight, auto-scrolled to the newest content.
// author: CloudDesk Team
// date: 2026-09-24

import { useEffect, useRef } from "react";
import { Sparkles } from "lucide-react";

import { ChatMessageBubble } from "@/components/chat/chat-message-bubble";
import { ChatProgressPanel } from "@/components/chat/chat-progress-panel";
import type { ChatMessage } from "@/hooks/use-conversation";
import type { ConversationStep } from "@/lib/api/types";

export function ChatMessageList({
  messages,
  steps,
}: {
  messages: ChatMessage[];
  steps: ConversationStep[];
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, steps]);

  if (messages.length === 0 && steps.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
        <div className="flex size-12 items-center justify-center rounded-full bg-primary/10">
          <Sparkles className="size-6 text-primary" strokeWidth={1.5} />
        </div>
        <div>
          <p className="text-sm font-medium">Ask CloudDesk AI Support anything</p>
          <p className="max-w-sm text-sm text-muted-foreground">
            Billing questions, account issues, or API problems — we&apos;ll route it to the right
            specialist automatically.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 py-2">
      {messages.map((message) => (
        <ChatMessageBubble key={message.id} message={message} />
      ))}
      <ChatProgressPanel steps={steps} />
      <div ref={bottomRef} />
    </div>
  );
}
