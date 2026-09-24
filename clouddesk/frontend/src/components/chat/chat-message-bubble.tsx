// name: components/chat/chat-message-bubble.tsx
// purpose: One chat bubble — visually distinct for the customer, the AI assistant, and quiet
//          inline system notices (e.g. "sent for review").
// author: CloudDesk Team
// date: 2026-09-24

import { Bot, User } from "lucide-react";

import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/hooks/use-conversation";

export function ChatMessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "system") {
    return (
      <div className="mx-auto max-w-md rounded-full bg-muted px-3.5 py-1.5 text-center text-xs text-muted-foreground">
        {message.text}
      </div>
    );
  }

  const isCustomer = message.role === "customer";
  return (
    <div className={cn("flex items-start gap-2.5", isCustomer && "flex-row-reverse")}>
      <div
        className={cn(
          "flex size-7 shrink-0 items-center justify-center rounded-full",
          isCustomer ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground"
        )}
      >
        {isCustomer ? <User className="size-3.5" /> : <Bot className="size-3.5" />}
      </div>
      <div
        className={cn(
          "max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
          isCustomer
            ? "rounded-tr-sm bg-primary text-primary-foreground"
            : "rounded-tl-sm bg-card text-card-foreground shadow-sm ring-1 ring-border"
        )}
      >
        {message.text}
      </div>
    </div>
  );
}
