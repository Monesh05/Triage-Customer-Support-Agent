// name: app/(portal)/billing/loading.tsx
// purpose: Automatic Next.js loading UI for the billing route.
// author: CloudDesk Team
// date: 2026-09-24

import { PageSkeleton } from "@/components/shared/page-skeleton";

export default function BillingLoading() {
  return <PageSkeleton statCount={0} />;
}
