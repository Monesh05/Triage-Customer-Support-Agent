"use client";

// name: app/support-console/tickets/error.tsx
// purpose: Route-level error boundary for the console tickets list.
// author: CloudDesk Team
// date: 2026-09-24

import { ErrorState } from "@/components/shared/error-state";

export default function ConsoleTicketsError({ reset }: { error: Error; reset: () => void }) {
  return <ErrorState message="We couldn't load the tickets list." onRetry={reset} />;
}
