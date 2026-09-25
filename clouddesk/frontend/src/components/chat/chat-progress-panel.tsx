// name: components/chat/chat-progress-panel.tsx
// purpose: The AI Support agent's live tool-execution timeline (spec section 11): renders only the
//          safe, high-level step labels the backend already redacted for customer consumption
//          (ConversationStep.step / .status), never raw agent reasoning, tool payloads, or stack
//          traces. Styled as a trustworthy "activity timeline" — a checklist of what the agent has
//          done so far — rather than a futuristic/chatbot-gimmick animation, per spec section 9's
//          "trustworthy enterprise AI, not a chatbot gimmick" direction.
// author: CloudDesk Team
// date: 2026-09-25

import { CheckCircle2, CircleDashed, Loader2, XCircle } from "lucide-react";

import type { ConversationStep } from "@/lib/api/types";
import { cn } from "@/lib/utils";

function StepIcon({ status }: { status: ConversationStep["status"] }) {
  if (status === "done") return <CheckCircle2 className="size-4 shrink-0 text-success" />;
  if (status === "failed") return <XCircle className="size-4 shrink-0 text-destructive" />;
  return <Loader2 className="size-4 shrink-0 animate-spin text-primary" />;
}

export function ChatProgressPanel({ steps }: { steps: ConversationStep[] }) {
  if (steps.length === 0) {
    return null;
  }

  const allDone = steps.every((step) => step.status === "done");

  return (
    <div className="ml-9.5 max-w-[80%] space-y-2.5 rounded-2xl rounded-tl-sm border border-border bg-card px-4 py-3 shadow-sm">
      <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        <CircleDashed className={cn("size-3.5", !allDone && "animate-pulse")} />
        {allDone ? "Analysis complete" : "AI Support is working on this"}
      </p>
      <ul className="space-y-1.5">
        {steps.map((step) => (
          <li
            key={step.step}
            className={cn(
              "flex items-start gap-2 text-sm leading-snug",
              step.status === "done" ? "text-muted-foreground" : "text-foreground"
            )}
          >
            <StepIcon status={step.status} />
            <span>{step.step}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
