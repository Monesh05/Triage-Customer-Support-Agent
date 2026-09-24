// name: components/console/specialist-findings-list.tsx
// purpose: Ticket Detail's "specialist findings" + "evidence" section (spec section 26): one card
//          per specialist agent (billing/account/technical/product) that ran on this ticket,
//          parsed from its output_summary. Internal staff, so full findings/evidence are shown
//          verbatim (already redacted/summarized at write time by Phase 7 observability).
// author: CloudDesk Team
// date: 2026-09-24

import { FlaskConical } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AgentRun } from "@/lib/api/types";
import { fieldAsString, fieldAsStringArray, parseAgentOutput } from "@/lib/parse-agent-output";
import { formatEnumLabel } from "@/lib/format";

const SPECIALIST_AGENTS: readonly string[] = ["billing", "account", "technical", "product"];

function SpecialistCard({ run }: { run: AgentRun }) {
  const output = parseAgentOutput(run.output_summary);
  const status = output ? fieldAsString(output, "status") : null;
  const findings = output ? fieldAsStringArray(output, "findings") : [];
  const evidence = output ? fieldAsStringArray(output, "evidence") : [];
  const recommendedActions = output ? fieldAsStringArray(output, "recommended_actions") : [];

  return (
    <Card className="border-border/70">
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm font-semibold capitalize">{run.agent_name} Agent</CardTitle>
        {status ? <StatusBadge status={status} /> : null}
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {findings.length > 0 ? (
          <div>
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Findings</p>
            <ul className="list-inside list-disc space-y-0.5 text-foreground">
              {findings.map((finding, index) => (
                <li key={index}>{finding}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {evidence.length > 0 ? (
          <div>
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Evidence</p>
            <div className="flex flex-wrap gap-1.5">
              {evidence.map((item, index) => (
                <code key={index} className="rounded bg-muted px-1.5 py-0.5 text-xs">
                  {item}
                </code>
              ))}
            </div>
          </div>
        ) : null}
        {recommendedActions.length > 0 ? (
          <div>
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Recommended actions
            </p>
            <ul className="list-inside list-disc space-y-0.5 text-foreground">
              {recommendedActions.map((action, index) => (
                <li key={index}>{action}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {!output && run.output_summary ? (
          <p className="text-muted-foreground">{run.output_summary}</p>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function SpecialistFindingsList({ runs }: { runs: AgentRun[] }) {
  const specialistRuns = runs.filter((run) => SPECIALIST_AGENTS.includes(run.agent_name));

  if (specialistRuns.length === 0) {
    return (
      <EmptyState
        icon={FlaskConical}
        title="No specialist findings"
        description="No billing, account, technical, or product agent ran for this ticket."
      />
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Assigned agents: {[...new Set(specialistRuns.map((r) => formatEnumLabel(r.agent_name)))].join(", ")}
      </p>
      {specialistRuns.map((run) => (
        <SpecialistCard key={run.run_id} run={run} />
      ))}
    </div>
  );
}
