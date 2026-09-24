// name: components/portal/api-keys-list.tsx
// purpose: /api page's key list. The backend never returns raw key material or a hash (spec
//          section 27), so this deliberately shows only status/metadata behind a masked,
//          decorative placeholder — no "reveal key" affordance that would imply a real secret is
//          on the page.
// author: CloudDesk Team
// date: 2026-09-24

import { KeyRound } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent } from "@/components/ui/card";
import type { ApiKey } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

export function ApiKeysList({ apiKeys }: { apiKeys: ApiKey[] }) {
  if (apiKeys.length === 0) {
    return (
      <Card className="border-border/70">
        <CardContent className="pt-6">
          <EmptyState icon={KeyRound} title="No API keys" description="No API keys have been issued for this account." />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {apiKeys.map((apiKey) => (
        <Card key={apiKey.id} className="border-border/70">
          <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
            <div className="flex items-center gap-3">
              <div className="flex size-9 items-center justify-center rounded-lg bg-secondary">
                <KeyRound className="size-4 text-secondary-foreground" />
              </div>
              <div>
                <p className="font-mono text-sm tracking-wide">cd_live_••••••••••••{apiKey.id.slice(0, 4)}</p>
                <p className="text-xs text-muted-foreground">
                  Created {formatDateTime(apiKey.created_at)} · Limit {apiKey.rate_limit.toLocaleString()} req/mo
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground">
                {apiKey.last_used_at ? `Last used ${formatDateTime(apiKey.last_used_at)}` : "Never used"}
              </span>
              <StatusBadge status={apiKey.status} />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
