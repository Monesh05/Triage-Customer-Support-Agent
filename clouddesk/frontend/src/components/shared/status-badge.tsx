// name: components/shared/status-badge.tsx
// purpose: One consistent color-coded badge for every status/priority enum rendered across the
//          portal and console (ticket status, approval status, payment status, incident severity,
//          agent run status, etc.), so status colors mean the same thing everywhere in the app.
// author: CloudDesk Team
// date: 2026-09-24

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { formatEnumLabel } from "@/lib/format";

export type StatusTone = "neutral" | "success" | "warning" | "danger" | "info";

const TONE_CLASSES: Record<StatusTone, string> = {
  neutral: "bg-secondary text-secondary-foreground border-transparent",
  success: "bg-success/15 text-success border-success/30 dark:text-success",
  warning: "bg-warning/20 text-warning-foreground border-warning/40",
  danger: "bg-destructive/10 text-destructive border-destructive/30",
  info: "bg-primary/10 text-primary border-primary/30",
};

/** Maps a known status string to a semantic tone. Falls back to "neutral" for anything unmapped
 * so a future enum value never crashes rendering — it just looks plain until mapped explicitly. */
const STATUS_TONE_MAP: Record<string, StatusTone> = {
  active: "success",
  succeeded: "success",
  paid: "success",
  completed: "success",
  resolved: "success",
  approved: "success",
  done: "success",
  success: "success",
  monitoring: "success",
  trialing: "info",
  in_progress: "info",
  investigating: "info",
  identified: "info",
  open: "info",
  pending: "warning",
  pending_approval: "warning",
  pending_customer: "warning",
  awaiting_approval: "warning",
  past_due: "warning",
  overdue: "warning",
  medium: "warning",
  high: "warning",
  locked: "danger",
  suspended: "danger",
  churned: "danger",
  failed: "danger",
  rejected: "danger",
  canceled: "danger",
  escalated: "danger",
  revoked: "danger",
  disabled: "danger",
  urgent: "danger",
  critical: "danger",
  failure: "danger",
};

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const tone = STATUS_TONE_MAP[status] ?? "neutral";
  return (
    <Badge variant="outline" className={cn(TONE_CLASSES[tone], "font-medium", className)}>
      {formatEnumLabel(status)}
    </Badge>
  );
}
