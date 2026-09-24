// name: app/(portal)/usage/loading.tsx
// purpose: Automatic Next.js loading UI for the usage route.
// author: CloudDesk Team
// date: 2026-09-24

import { PageSkeleton } from "@/components/shared/page-skeleton";

export default function UsageLoading() {
  return <PageSkeleton statCount={0} />;
}
