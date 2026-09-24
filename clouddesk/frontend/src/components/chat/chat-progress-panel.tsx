// name: components/chat/chat-progress-panel.tsx
// purpose: The "AI Support Team" live progress display (spec section 25's
//          "✓ Understanding request / ⟳ Preparing resolution" example) — renders only the safe,
//          high-level step labels the backend already redacted for customer consumption, never
//          raw agent reasoning or tool payloads.
// author: CloudDesk Team
// date: 2026-09-24

import { CheckCircle2, CircleDashed, Loader2, XCircle } from "lucide-react";

import type { ConversationStep } from "@/lib/api/types";
import { cn } from "@/lib/utils";

function StepIcon({ status }: { status: ConversationStep["status"] }) {
  if (status === "done") return <CheckCircle2 className="size-4 text-success" />;
  if (status === "failed") return <XCircle className="size-4 text-destructive" />;
  return <Loader2 className="size-4 animate-spin text-primary" />;
}

export function ChatProgressPanel({ steps }: { steps: ConversationStep[] }) {
  if (steps.length === 0) {
    return null;
  }

  return (
    <div className="ml-9.5 max-w-[80%] space-y-2 rounded-2xl rounded-tl-sm border border-border bg-card px-4 py-3 shadow-sm">
      <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        <CircleDashed className="size-3.5" />
        AI Support Team
      </p>
      <ul className="space-y-1.5">
        {steps.map((step) => (
          <li
            key={step.step}
            className={cn(
              "flex items-center gap-2 text-sm",
              step.status === "done" ? "text-muted-foreground" : "text-foreground"
            )}
          >
            <StepIcon status={step.status} />
            {step.step}
          </li>
        ))}
      </ul>
    </div>
  );
}
