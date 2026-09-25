// name: components/portal/stat-card.tsx
// purpose: A single quick-stat "MetricCard" tile (spec sections 4 and 15) reused across the
//          dashboard and usage page — small label, large primary value, secondary context, and a
//          small icon, all at a consistent height so a row of these always lines up.
// author: CloudDesk Team
// date: 2026-09-25

import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  tone = "default",
}: {
  label: string;
  value: string;
  hint?: string;
  icon: LucideIcon;
  tone?: "default" | "warning" | "danger";
}) {
  const toneClasses =
    tone === "warning"
      ? "bg-warning/15 text-warning-foreground"
      : tone === "danger"
        ? "bg-destructive/10 text-destructive"
        : "bg-primary/10 text-primary";

  return (
    <Card className="h-full border-border/70 transition-shadow hover:shadow-sm">
      <CardContent className="flex h-full items-start justify-between gap-3 px-5 py-4">
        <div className="space-y-1.5">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          <p className="text-2xl font-semibold tracking-tight">{value}</p>
          {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
        </div>
        <div className={cn("flex size-9 shrink-0 items-center justify-center rounded-lg", toneClasses)}>
          <Icon className="size-4.5" strokeWidth={2} />
        </div>
      </CardContent>
    </Card>
  );
}
