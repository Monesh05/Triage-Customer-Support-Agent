// name: app/support-console/tickets/[id]/loading.tsx
// purpose: Automatic Next.js loading UI for the ticket detail route.
// author: CloudDesk Team
// date: 2026-09-24

import { Skeleton } from "@/components/ui/skeleton";

export default function TicketDetailLoading() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-4 w-32" />
      <Skeleton className="h-40 rounded-xl" />
      <Skeleton className="h-64 rounded-xl" />
    </div>
  );
}
