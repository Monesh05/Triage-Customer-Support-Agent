// name: lib/parse-agent-output.ts
// purpose: Agent output_summary fields on an AgentRun are persisted as JSON-encoded strings (see
//          the real trace data from GET /tickets/{id}/trace) but typed as `string | null` by the
//          backend schema — there is no structured schema for "whatever this agent's structured
//          output looked like". This helper safely parses that JSON for display in the Support
//          Console without ever using `any`: unknown + a narrow type guard at the boundary.
// author: CloudDesk Team
// date: 2026-09-24

export type AgentOutputRecord = Record<string, unknown>;

function isPlainRecord(value: unknown): value is AgentOutputRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Parse an AgentRun's `output_summary` as a JSON object if possible; otherwise `null`, so
 * callers can fall back to rendering the raw string instead. */
export function parseAgentOutput(outputSummary: string | null): AgentOutputRecord | null {
  if (!outputSummary) return null;
  try {
    const parsed: unknown = JSON.parse(outputSummary);
    return isPlainRecord(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function fieldAsString(record: AgentOutputRecord, key: string): string | null {
  const value = record[key];
  return typeof value === "string" ? value : null;
}

export function fieldAsStringArray(record: AgentOutputRecord, key: string): string[] {
  const value = record[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}
