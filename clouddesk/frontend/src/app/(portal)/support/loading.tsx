// name: app/(portal)/support/loading.tsx
// purpose: Automatic Next.js loading UI for the support/chat route.
// author: CloudDesk Team
// date: 2026-09-24

import { Skeleton } from "@/components/ui/skeleton";

export default function SupportLoading() {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-4 w-80" />
      </div>
      <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
        <Skeleton className="h-[calc(100vh-9.5rem)] rounded-xl" />
        <Skeleton className="hidden h-96 rounded-xl lg:block" />
      </div>
    </div>
  );
}
