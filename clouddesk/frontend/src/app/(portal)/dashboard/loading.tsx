// name: app/(portal)/dashboard/loading.tsx
// purpose: Automatic Next.js loading UI for the dashboard route while server data is fetched.
// author: CloudDesk Team
// date: 2026-09-24

import { PageSkeleton } from "@/components/shared/page-skeleton";

export default function DashboardLoading() {
  return <PageSkeleton />;
}
