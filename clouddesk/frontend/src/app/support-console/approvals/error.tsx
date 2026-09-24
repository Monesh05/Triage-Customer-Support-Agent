"use client";

// name: app/support-console/approvals/error.tsx
// purpose: Route-level error boundary for the approval queue page.
// author: CloudDesk Team
// date: 2026-09-24

import { ErrorState } from "@/components/shared/error-state";

export default function ApprovalQueueError({ reset }: { error: Error; reset: () => void }) {
  return <ErrorState message="We couldn't load the approval queue." onRetry={reset} />;
}
