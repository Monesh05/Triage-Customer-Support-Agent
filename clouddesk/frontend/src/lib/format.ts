// name: lib/format.ts
// purpose: Small formatting helpers (currency/date/relative time) shared across portal and
//          console pages, so every page renders numbers/dates consistently.
// author: CloudDesk Team
// date: 2026-09-24

export function formatCurrency(amount: number, currency: string = "USD"): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(amount);
}

export function formatDate(isoDate: string): string {
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(new Date(isoDate));
}

export function formatDateTime(isoDate: string): string {
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(isoDate)
  );
}

export function formatDurationMs(durationMs: number): string {
  if (durationMs < 1000) {
    return `${durationMs}ms`;
  }
  return `${(durationMs / 1000).toFixed(1)}s`;
}

/** Title-case a snake_case enum value for display, e.g. "past_due" -> "Past Due". */
export function formatEnumLabel(value: string): string {
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
