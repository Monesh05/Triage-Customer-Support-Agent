"use client";

// name: app/support-console/tickets/[id]/error.tsx
// purpose: Route-level error boundary for the ticket detail page.
// author: CloudDesk Team
// date: 2026-09-24

import { ErrorState } from "@/components/shared/error-state";

export default function TicketDetailError({ reset }: { error: Error; reset: () => void }) {
  return <ErrorState message="We couldn't load this ticket." onRetry={reset} />;
}
