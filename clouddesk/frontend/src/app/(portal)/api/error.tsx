"use client";

// name: app/(portal)/api/error.tsx
// purpose: Route-level error boundary for the API keys page.
// author: CloudDesk Team
// date: 2026-09-24

import { ErrorState } from "@/components/shared/error-state";

export default function ApiKeysError({ reset }: { error: Error; reset: () => void }) {
  return <ErrorState message="We couldn't load your API keys." onRetry={reset} />;
}
