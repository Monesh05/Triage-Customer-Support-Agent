// name: components/portal/incident-banner.tsx
// purpose: A dashboard banner surfacing active (unresolved) service incidents, per spec section
//          25's "active service incidents banner if relevant to the customer". Renders nothing
//          when there is nothing active, rather than an empty/placeholder banner.
// author: CloudDesk Team
// date: 2026-09-24

import { TriangleAlert } from "lucide-react";

import { StatusBadge } from "@/components/shared/status-badge";
import type { ServiceIncident } from "@/lib/api/types";

export function IncidentBanner({ incidents }: { incidents: ServiceIncident[] }) {
  const activeIncidents = incidents.filter((incident) => incident.status !== "resolved");
  if (activeIncidents.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2 rounded-xl border border-warning/40 bg-warning/10 px-4 py-3">
      {activeIncidents.map((incident) => (
        <div key={incident.id} className="flex flex-wrap items-start gap-2.5">
          <TriangleAlert className="mt-0.5 size-4.5 shrink-0 text-warning-foreground" strokeWidth={2} />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-medium text-warning-foreground">{incident.service_name}</p>
              <StatusBadge status={incident.status} />
              <StatusBadge status={incident.severity} />
            </div>
            <p className="text-sm text-warning-foreground/90">{incident.description}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
