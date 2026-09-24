// name: components/shared/error-state.tsx
// purpose: One consistent, calm error display for a failed data fetch (never a raw stack trace
//          or fetch error dumped to the page), with an optional retry affordance.
// author: CloudDesk Team
// date: 2026-09-24

"use client";

import { AlertTriangle, RotateCw } from "lucide-react";

import { Button } from "@/components/ui/button";

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-destructive/30 bg-destructive/5 px-6 py-14 text-center">
      <div className="flex size-12 items-center justify-center rounded-full bg-destructive/10">
        <AlertTriangle className="size-6 text-destructive" strokeWidth={1.5} />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">Something went wrong</p>
        <p className="max-w-sm text-sm text-muted-foreground">{message}</p>
      </div>
      {onRetry ? (
        <Button variant="outline" size="sm" onClick={onRetry} className="mt-1 gap-1.5">
          <RotateCw className="size-3.5" />
          Try again
        </Button>
      ) : null}
    </div>
  );
}
