"use client";

// name: components/console/agent-trace-timeline.tsx
// purpose: The Agent Trace view (spec section 26): the ordered execution sequence
//          (Triage -> Billing -> ... -> QA) with per-step status/duration, expandable to the full
//          internal detail (tool calls, tool results, errors) — appropriate here since this is
//          internal tooling, unlike the customer-facing chat's redacted step list.
// author: CloudDesk Team
// date: 2026-09-24

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

import { StatusBadge } from "@/components/shared/status-badge";
import type { AgentRun } from "@/lib/api/types";
import { formatDurationMs, formatEnumLabel } from "@/lib/format";
import { cn } from "@/lib/utils";

function RunDetailJson({ label, value }: { label: string; value: unknown }) {
  const isEmpty = Array.isArray(value) && value.length === 0;
  if (isEmpty) return null;
  return (
    <div>
      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <pre className="overflow-x-auto rounded-lg bg-muted/70 p-2.5 text-xs leading-relaxed">
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}

function TraceRow({ run, isLast }: { run: AgentRun; isLast: boolean }) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <li className="relative pl-8">
      {!isLast ? <span className="absolute left-[11px] top-6 h-full w-px bg-border" /> : null}
      <span
        className={cn(
          "absolute left-0 top-1 flex size-6 items-center justify-center rounded-full text-[10px] font-semibold",
          run.status === "success" ? "bg-success/20 text-success" : "bg-destructive/20 text-destructive"
        )}
      >
        {run.status === "success" ? "OK" : "!"}
      </span>
      <button
        type="button"
        onClick={() => setIsExpanded((prev) => !prev)}
        className="flex w-full items-center justify-between gap-3 rounded-lg py-1.5 text-left hover:bg-muted/50"
      >
        <span className="flex items-center gap-2">
          {isExpanded ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
          <span className="text-sm font-medium capitalize">{run.agent_name}</span>
          {run.iteration ? <span className="text-xs text-muted-foreground">iteration {run.iteration}</span> : null}
        </span>
        <span className="flex items-center gap-2 text-xs text-muted-foreground">
          {formatDurationMs(run.duration_ms)}
          <StatusBadge status={run.status} />
        </span>
      </button>
      {isExpanded ? (
        <div className="ml-5 mt-1 space-y-2.5 rounded-lg border border-border bg-card p-3">
          {run.input_summary ? (
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Input</p>
              <p className="text-sm">{run.input_summary}</p>
            </div>
          ) : null}
          {run.output_summary ? (
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Output</p>
              <p className="whitespace-pre-wrap text-sm">{run.output_summary}</p>
            </div>
          ) : null}
          <RunDetailJson label="Tool calls" value={run.tool_calls} />
          <RunDetailJson label="Tool results" value={run.tool_results} />
          {run.error ? (
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-destructive">Error</p>
              <p className="text-sm text-destructive">{run.error}</p>
            </div>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}

export function AgentTraceTimeline({ runs }: { runs: AgentRun[] }) {
  if (runs.length === 0) {
    return <p className="text-sm text-muted-foreground">No agent runs recorded for this ticket yet.</p>;
  }

  return (
    <div className="space-y-1">
      <p className="mb-2 text-xs text-muted-foreground">
        {runs.map((run) => formatEnumLabel(run.agent_name)).join(" → ")}
      </p>
      <ul className="space-y-0.5">
        {runs.map((run, index) => (
          <TraceRow key={run.run_id} run={run} isLast={index === runs.length - 1} />
        ))}
      </ul>
    </div>
  );
}
