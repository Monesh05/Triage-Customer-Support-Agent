"use client";

// name: components/chat/chat-input-bar.tsx
// purpose: The chat's message composer: textarea + send button, submitting on Enter (Shift+Enter
//          for a newline) and disabled while a request is in flight.
// author: CloudDesk Team
// date: 2026-09-24

import { useState } from "react";
import { SendHorizonal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { CHAT_MESSAGE_MAX_LENGTH } from "@/lib/constants";

export function ChatInputBar({
  isBusy,
  onSend,
}: {
  isBusy: boolean;
  onSend: (text: string) => void;
}) {
  const [draft, setDraft] = useState("");

  function submit() {
    const trimmed = draft.trim();
    if (!trimmed || isBusy) return;
    onSend(trimmed);
    setDraft("");
  }

  return (
    <div className="flex items-end gap-2 border-t border-border bg-background p-3">
      <Textarea
        value={draft}
        maxLength={CHAT_MESSAGE_MAX_LENGTH}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        placeholder="Describe what you need help with..."
        rows={1}
        className="max-h-32 min-h-10 resize-none"
        disabled={isBusy}
      />
      <Button size="icon" onClick={submit} disabled={isBusy || !draft.trim()} aria-label="Send message">
        <SendHorizonal className="size-4" />
      </Button>
    </div>
  );
}
