// name: app/support-console/approvals/loading.tsx
// purpose: Automatic Next.js loading UI for the approval queue route.
// author: CloudDesk Team
// date: 2026-09-24

import { Skeleton } from "@/components/ui/skeleton";

export default function ApprovalQueueLoading() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-4 w-64" />
      </div>
      <Skeleton className="h-10 w-64" />
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-24 rounded-xl" />
        ))}
      </div>
    </div>
  );
}
