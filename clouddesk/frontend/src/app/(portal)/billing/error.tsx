"use client";

// name: app/(portal)/billing/error.tsx
// purpose: Route-level error boundary for the billing page.
// author: CloudDesk Team
// date: 2026-09-24

import { ErrorState } from "@/components/shared/error-state";

export default function BillingError({ reset }: { error: Error; reset: () => void }) {
  return <ErrorState message="We couldn't load your billing information." onRetry={reset} />;
}
