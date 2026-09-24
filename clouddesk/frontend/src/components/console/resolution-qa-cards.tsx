// name: components/console/resolution-qa-cards.tsx
// purpose: Ticket Detail's "resolution", "QA result", and "escalation" sections (spec section
//          26). Grouped in one file since each is a small, single-field-set card of the same
//          shape, parsed from the corresponding agent's output_summary.
// author: CloudDesk Team
// date: 2026-09-24

import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AgentRun } from "@/lib/api/types";
import { fieldAsString, parseAgentOutput } from "@/lib/parse-agent-output";

function LatestRunOf(runs: AgentRun[], agentName: string): AgentRun | undefined {
  return [...runs].reverse().find((run) => run.agent_name === agentName);
}

export function ResolutionCard({ runs }: { runs: AgentRun[] }) {
  const run = LatestRunOf(runs, "resolution");
  if (!run) return null;
  const output = parseAgentOutput(run.output_summary);
  const summary = output ? fieldAsString(output, "summary") : run.output_summary;
  const proposedResolution = output ? fieldAsString(output, "proposed_resolution") : null;

  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle className="text-base">Resolution</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {summary ? <p>{summary}</p> : null}
        {proposedResolution ? (
          <p className="rounded-lg bg-muted/60 p-3 text-foreground">{proposedResolution}</p>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function QaResultCard({ runs }: { runs: AgentRun[] }) {
  const run = LatestRunOf(runs, "qa");
  if (!run) return null;
  const output = parseAgentOutput(run.output_summary);
  const verdict = output ? fieldAsString(output, "verdict") ?? fieldAsString(output, "decision") : null;
  const feedback = output ? fieldAsString(output, "feedback") : null;

  return (
    <Card className="border-border/70">
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-base">QA result</CardTitle>
        <StatusBadge status={run.status} />
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {verdict ? <p className="font-medium capitalize">{verdict}</p> : null}
        {feedback ? <p className="text-muted-foreground">{feedback}</p> : run.output_summary ? (
          <p className="text-muted-foreground">{run.output_summary}</p>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function EscalationCard({ runs }: { runs: AgentRun[] }) {
  const run = LatestRunOf(runs, "escalation");
  if (!run) return null;

  return (
    <Card className="border-destructive/40 bg-destructive/5">
      <CardHeader>
        <CardTitle className="text-base text-destructive">Escalated to a human</CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-foreground">
        {run.output_summary ?? "This ticket was escalated for human review."}
      </CardContent>
    </Card>
  );
}
