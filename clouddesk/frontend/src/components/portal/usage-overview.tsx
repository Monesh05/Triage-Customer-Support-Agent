// name: components/portal/usage-overview.tsx
// purpose: /usage page's centerpiece: current-period API usage vs. the plan's rate limit as a
//          progress bar, plus a lightweight historical bar-per-period view (no charting library
//          needed for a handful of periods — plain proportional bars keep the bundle small).
// author: CloudDesk Team
// date: 2026-09-24

import { BarChart3 } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { UsageRecord } from "@/lib/api/types";
import { formatDate } from "@/lib/format";

const NEAR_LIMIT_THRESHOLD_PERCENT: number = 80;

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
  const maxHistoricalCalls = Math.max(...sorted.map((record) => record.api_calls), 1);

  return (
    <div className="space-y-4">
      <Card className="border-border/70">
        <CardHeader>
          <CardTitle className="text-base">Current period</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-semibold tracking-tight">
              {current.api_calls.toLocaleString()}
            </span>
            <span className="text-sm text-muted-foreground">
              of {apiRateLimit.toLocaleString()} calls
            </span>
          </div>
          <Progress
            value={currentPercent}
            className={currentPercent >= NEAR_LIMIT_THRESHOLD_PERCENT ? "[&>div]:bg-warning" : undefined}
          />
          <p className="text-xs text-muted-foreground">
            {formatDate(current.period_start)} – {formatDate(current.period_end)} · {currentPercent}% of limit
          </p>
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
