"use client";

// name: components/chat/chat-panel.tsx
// purpose: The AI Support chat's main panel (spec section 25): wires the useConversation hook to
//          the message list and input bar, and surfaces a calm error banner if the API becomes
//          unreachable mid-conversation. 2026-09-25 redesign (spec section 9): a compact header
//          ("CloudDesk AI Support · Online") so the panel reads as a real product surface, not a
//          bare empty box; the "Online" indicator is a static availability label (the chat really
//          is always reachable while this page is up), not a fabricated live metric.
// author: CloudDesk Team
// date: 2026-09-25

import { AlertTriangle } from "lucide-react";

import { ChatInputBar } from "@/components/chat/chat-input-bar";
import { ChatMessageList } from "@/components/chat/chat-message-list";
import { Card } from "@/components/ui/card";
import { useConversation } from "@/hooks/use-conversation";

export function ChatPanel({ customerId }: { customerId: string }) {
  const { messages, steps, isBusy, error, sendMessage } = useConversation(customerId);

  return (
    <Card className="flex h-full min-h-0 flex-col overflow-hidden border-border/70 p-0">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <p className="text-sm font-semibold">CloudDesk AI Support</p>
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className="size-1.5 rounded-full bg-success" aria-hidden />
          Online
        </span>
      </div>
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
