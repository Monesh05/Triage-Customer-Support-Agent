"use client";

// name: app/(portal)/support/error.tsx
// purpose: Route-level error boundary for the support/chat page.
// author: CloudDesk Team
// date: 2026-09-24

import { ErrorState } from "@/components/shared/error-state";

export default function SupportError({ reset }: { error: Error; reset: () => void }) {
  return <ErrorState message="We couldn't load AI Support right now." onRetry={reset} />;
}
