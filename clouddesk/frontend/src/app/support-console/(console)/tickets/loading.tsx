// name: app/support-console/tickets/loading.tsx
// purpose: Automatic Next.js loading UI for the console tickets list.
// author: CloudDesk Team
// date: 2026-09-24

import { Skeleton } from "@/components/ui/skeleton";

export default function ConsoleTicketsLoading() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-4 w-72" />
      </div>
      <Skeleton className="h-96 rounded-xl" />
    </div>
  );
}
