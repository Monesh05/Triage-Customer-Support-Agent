// name: components/portal/incident-banner.tsx
// purpose: Dashboard "account health" section (spec section 3): a compact one-line health summary
//          ("2 issues require attention" / "All systems operational") followed by a clean list of
//          active service incidents — category, status, severity, and a short description — each
//          severity colored subtly rather than as a large warning box. Renders nothing when there
//          are no active incidents besides the "all healthy" summary line.
// author: CloudDesk Team
// date: 2026-09-25

import { CheckCircle2 } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/status-badge";
import type { ServiceIncident } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const SEVERITY_DOT_CLASSES: Record<string, string> = {
  critical: "bg-destructive",
  high: "bg-destructive",
  medium: "bg-warning",
  low: "bg-muted-foreground",
};

function severityDotClass(severity: string): string {
  return SEVERITY_DOT_CLASSES[severity] ?? "bg-muted-foreground";
}

export function IncidentBanner({ incidents }: { incidents: ServiceIncident[] }) {
  const activeIncidents = incidents.filter((incident) => incident.status !== "resolved");

  return (
    <Card className="border-border/70">
      <CardHeader className="pb-1">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          {activeIncidents.length === 0 ? (
            <>
              <CheckCircle2 className="size-4 text-success" />
              <span>Account health</span>
              <span className="font-normal text-muted-foreground">· All systems operational</span>
            </>
          ) : (
            <>
              <span
                className="inline-flex size-2 rounded-full bg-warning"
                aria-hidden
              />
              <span>Account health</span>
              <span className="font-normal text-muted-foreground">
                · {activeIncidents.length} {activeIncidents.length === 1 ? "issue" : "issues"} require
                attention
              </span>
            </>
          )}
        </CardTitle>
      </CardHeader>
      {activeIncidents.length > 0 ? (
        <CardContent className="pt-2">
          <ul className="divide-y divide-border">
            {activeIncidents.map((incident) => (
              <li key={incident.id} className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
                <span
                  className={cn("mt-1.5 size-1.5 shrink-0 rounded-full", severityDotClass(incident.severity))}
                  aria-hidden
                />
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-medium">{incident.service_name}</p>
                    <StatusBadge status={incident.status} />
                    <StatusBadge status={incident.severity} />
                  </div>
                  <p className="text-sm text-muted-foreground">{incident.description}</p>
                </div>
              </li>
            ))}
          </ul>
        </CardContent>
      ) : null}
    </Card>
  );
}
