// name: app/(portal)/support/tickets/[id]/loading.tsx
// purpose: Automatic Next.js loading UI for the customer-facing ticket detail route.
// author: CloudDesk Team
// date: 2026-09-25

import { PageSkeleton } from "@/components/shared/page-skeleton";

export default function TicketDetailLoading() {
  return <PageSkeleton statCount={0} />;
}
