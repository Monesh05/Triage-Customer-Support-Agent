"use client";

// name: app/(portal)/usage/error.tsx
// purpose: Route-level error boundary for the usage page.
// author: CloudDesk Team
// date: 2026-09-24

import { ErrorState } from "@/components/shared/error-state";

export default function UsageError({ reset }: { error: Error; reset: () => void }) {
  return <ErrorState message="We couldn't load your usage data." onRetry={reset} />;
}
