// name: components/console/ticket-overview-card.tsx
// purpose: Ticket Detail's top card (spec section 26): the customer's original message plus the
//          Triage Agent's detected intent/priority/sentiment, parsed from its output_summary.
// author: CloudDesk Team
// date: 2026-09-24

import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AgentRun, SupportTicket } from "@/lib/api/types";
import { fieldAsString, fieldAsStringArray, parseAgentOutput } from "@/lib/parse-agent-output";

export function TicketOverviewCard({
  ticket,
  triageRun,
}: {
  ticket: SupportTicket;
  triageRun: AgentRun | undefined;
}) {
  const triageOutput = triageRun ? parseAgentOutput(triageRun.output_summary) : null;
  const intents = triageOutput ? fieldAsStringArray(triageOutput, "intents") : [];
  const sentiment = triageOutput ? fieldAsString(triageOutput, "sentiment") : null;
  const reason = triageOutput ? fieldAsString(triageOutput, "reason") : null;

  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle className="text-base">{ticket.subject}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="rounded-lg bg-muted/60 p-3 text-sm leading-relaxed text-foreground">
          {ticket.description}
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={ticket.priority} />
          <StatusBadge status={ticket.status} />
          {intents.map((intent) => (
            <StatusBadge key={intent} status={intent} className="bg-primary/10 text-primary border-primary/30" />
          ))}
          {sentiment ? (
            <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs text-secondary-foreground">
              Sentiment: {sentiment}
            </span>
          ) : null}
        </div>
        {reason ? <p className="text-sm text-muted-foreground">{reason}</p> : null}
      </CardContent>
    </Card>
  );
}
