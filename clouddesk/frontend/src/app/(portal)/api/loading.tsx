// name: app/(portal)/api/loading.tsx
// purpose: Automatic Next.js loading UI for the API keys route.
// author: CloudDesk Team
// date: 2026-09-24

import { PageSkeleton } from "@/components/shared/page-skeleton";

export default function ApiKeysLoading() {
  return <PageSkeleton statCount={0} />;
}
