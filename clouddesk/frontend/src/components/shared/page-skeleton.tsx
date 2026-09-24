// name: components/shared/page-skeleton.tsx
// purpose: A generic "stat cards + content cards" loading skeleton reused by loading.tsx files
//          across the portal/console, so route transitions never show a blank flash.
// author: CloudDesk Team
// date: 2026-09-24

import { Skeleton } from "@/components/ui/skeleton";

export function PageSkeleton({ statCount = 3 }: { statCount?: number }) {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-4 w-96" />
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        {Array.from({ length: statCount }).map((_, index) => (
          <Skeleton key={index} className="h-24 rounded-xl" />
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-56 rounded-xl" />
        <Skeleton className="h-56 rounded-xl" />
      </div>
    </div>
  );
}
