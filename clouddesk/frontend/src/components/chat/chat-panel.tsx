"use client";

// name: components/chat/chat-panel.tsx
// purpose: The AI Support chat's main panel (spec section 25): wires the useConversation hook to
//          the message list and input bar, and surfaces a calm error banner if the API becomes
//          unreachable mid-conversation.
// author: CloudDesk Team
// date: 2026-09-24

import { AlertTriangle } from "lucide-react";

import { ChatInputBar } from "@/components/chat/chat-input-bar";
import { ChatMessageList } from "@/components/chat/chat-message-list";
import { Card } from "@/components/ui/card";
import { useConversation } from "@/hooks/use-conversation";

export function ChatPanel({ customerId }: { customerId: string }) {
  const { messages, steps, isBusy, error, sendMessage } = useConversation(customerId);

  return (
    <Card className="flex h-[calc(100vh-9.5rem)] flex-col overflow-hidden border-border/70 p-0">
      <div className="flex-1 overflow-y-auto px-4">
        <ChatMessageList messages={messages} steps={steps} />
      </div>
      {error ? (
        <div className="mx-4 mb-2 flex items-center gap-2 rounded-lg bg-destructive/10 px-3 py-2 text-xs text-destructive">
          <AlertTriangle className="size-3.5 shrink-0" />
          {error}
        </div>
      ) : null}
      <ChatInputBar isBusy={isBusy} onSend={sendMessage} />
    </Card>
  );
}
