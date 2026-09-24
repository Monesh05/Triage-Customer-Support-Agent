// name: components/portal/stat-card.tsx
// purpose: A single quick-stat tile for the dashboard (usage this period, next invoice, account
//          status, etc.) — a small, reusable presentational building block.
// author: CloudDesk Team
// date: 2026-09-24

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
    <Card className="border-border/70">
      <CardContent className="flex items-start justify-between gap-3 px-5 py-4">
        <div className="space-y-1">
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
