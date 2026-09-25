"use client";

// name: components/portal/api-keys-list.tsx
// purpose: /api page's key list. The backend never returns raw key material or a hash (spec
//          section 27), so this deliberately shows only status/metadata behind a masked,
//          decorative placeholder — no "Reveal"/"Revoke" affordance that would imply a real secret
//          or a real revoke endpoint exists (there is no such endpoint on the backend; adding those
//          buttons would be a dead click, which the redesign brief explicitly warns against).
//          "Copy" copies the key's real id (the only identifier the API actually returns) and
//          confirms via the existing toast setup — spec section 17's "copy-to-clipboard
//          confirmation" microinteraction, spec section 8's professional developer-platform look.
// author: CloudDesk Team
// date: 2026-09-25

import { Check, Copy, KeyRound } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { ApiKey } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";

function CopyKeyIdButton({ apiKeyId }: { apiKeyId: string }) {
  const [justCopied, setJustCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(apiKeyId);
      setJustCopied(true);
      toast.success("Key ID copied to clipboard");
      window.setTimeout(() => setJustCopied(false), 1500);
    } catch {
      toast.error("Could not copy to clipboard");
    }
  }

  return (
    <Button variant="ghost" size="icon-sm" onClick={handleCopy} aria-label="Copy key ID">
      {justCopied ? <Check className="size-3.5 text-success" /> : <Copy className="size-3.5" />}
    </Button>
  );
}

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
        <Card key={apiKey.id} className="border-border/70 transition-shadow hover:shadow-sm">
          <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
            <div className="flex items-center gap-3">
              <div className="flex size-9 items-center justify-center rounded-lg bg-secondary">
                <KeyRound className="size-4 text-secondary-foreground" />
              </div>
              <div>
                <div className="flex items-center gap-1">
                  <p className="font-mono text-sm tracking-wide">cd_live_••••••••••••{apiKey.id.slice(0, 4)}</p>
                  <CopyKeyIdButton apiKeyId={apiKey.id} />
                </div>
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
