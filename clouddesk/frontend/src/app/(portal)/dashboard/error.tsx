"use client";

// name: app/(portal)/dashboard/error.tsx
// purpose: Route-level error boundary for the dashboard: catches a failed server fetch (e.g. the
//          backend being down) and shows a calm retry UI instead of Next's default error page.
// author: CloudDesk Team
// date: 2026-09-24

import { ErrorState } from "@/components/shared/error-state";

export default function DashboardError({ reset }: { error: Error; reset: () => void }) {
  return (
    <ErrorState
      message="We couldn't load your dashboard. The CloudDesk API may be unreachable."
      onRetry={reset}
    />
  );
}
