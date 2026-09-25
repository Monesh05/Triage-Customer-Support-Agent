// name: components/portal/usage-overview.tsx
// purpose: /usage page's centerpiece: current-period API usage vs. the plan's rate limit as a
//          polished progress bar plus supporting metric tiles (spec section 7 — current usage,
//          monthly limit, remaining, reset date, all derived from the same UsageRecord the
//          progress bar uses, never fabricated), and a lightweight historical bar-per-period view
//          (no charting library needed for a handful of periods — plain proportional bars keep the
//          bundle small).
// author: CloudDesk Team
// date: 2026-09-25

import { BarChart3 } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { UsageRecord } from "@/lib/api/types";
import { formatDate } from "@/lib/format";

const NEAR_LIMIT_THRESHOLD_PERCENT: number = 80;

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold tracking-tight">{value}</p>
    </div>
  );
}

export function UsageOverview({
  usageRecords,
  apiRateLimit,
}: {
  usageRecords: UsageRecord[];
  apiRateLimit: number;
}) {
  if (usageRecords.length === 0) {
    return (
      <Card className="border-border/70">
        <CardContent className="pt-6">
          <EmptyState icon={BarChart3} title="No usage recorded yet" description="Usage will appear once API calls are made." />
        </CardContent>
      </Card>
    );
  }

  const sorted = [...usageRecords].sort(
    (a, b) => new Date(b.period_start).getTime() - new Date(a.period_start).getTime()
  );
  const [current, ...history] = sorted;
  const currentPercent = Math.min(100, Math.round((current.api_calls / apiRateLimit) * 100));
  const remaining = Math.max(0, apiRateLimit - current.api_calls);
  const maxHistoricalCalls = Math.max(...sorted.map((record) => record.api_calls), 1);

  return (
    <div className="space-y-4">
      <Card className="border-border/70">
        <CardHeader>
          <CardTitle className="text-base">API usage</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="space-y-2">
            <div className="flex items-baseline justify-between">
              <span className="text-2xl font-semibold tracking-tight">
                {current.api_calls.toLocaleString()}
                <span className="ml-1 text-base font-normal text-muted-foreground">
                  / {apiRateLimit.toLocaleString()} calls
                </span>
              </span>
              <span className="text-sm font-medium text-muted-foreground">{currentPercent}% of limit</span>
            </div>
            <Progress
              value={currentPercent}
              className={currentPercent >= NEAR_LIMIT_THRESHOLD_PERCENT ? "[&>div]:bg-warning" : undefined}
            />
            <p className="text-xs text-muted-foreground">
              {formatDate(current.period_start)} – {formatDate(current.period_end)}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4 border-t border-border pt-4 sm:grid-cols-4">
            <MetricTile label="Current usage" value={current.api_calls.toLocaleString()} />
            <MetricTile label="Monthly limit" value={apiRateLimit.toLocaleString()} />
            <MetricTile label="Remaining" value={remaining.toLocaleString()} />
            <MetricTile label="Reset date" value={formatDate(current.period_end)} />
          </div>
        </CardContent>
      </Card>

      {history.length > 0 ? (
        <Card className="border-border/70">
          <CardHeader>
            <CardTitle className="text-base">Previous periods</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {history.map((record) => (
              <div key={record.id} className="space-y-1">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{formatDate(record.period_start)}</span>
                  <span>{record.api_calls.toLocaleString()} calls</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-chart-2"
                    style={{ width: `${Math.max(4, (record.api_calls / maxHistoricalCalls) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
