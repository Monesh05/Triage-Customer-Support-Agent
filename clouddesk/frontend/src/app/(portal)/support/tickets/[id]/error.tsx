"use client";

// name: app/(portal)/support/tickets/[id]/error.tsx
// purpose: Route-level error boundary for the customer-facing ticket detail page (covers a 404
//          for an unknown ticket id and a 403 for a ticket that does not belong to the current
//          customer, both surfaced as ApiError by lib/api/client.ts).
// author: CloudDesk Team
// date: 2026-09-25

import { ErrorState } from "@/components/shared/error-state";

export default function TicketDetailError({ reset }: { error: Error; reset: () => void }) {
  return <ErrorState message="We couldn't load this ticket." onRetry={reset} />;
}
