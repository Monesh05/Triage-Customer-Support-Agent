// name: app/(portal)/api/page.tsx
// purpose: Customer portal API key status page (spec section 25). Server Component.
// author: CloudDesk Team
// date: 2026-09-24

import { ApiKeysList } from "@/components/portal/api-keys-list";
import { getApiKeys } from "@/lib/api/billing";
import { getCurrentCustomerId } from "@/lib/current-customer";

// Always fetch fresh per-customer data server-side rather than being statically prerendered.
export const dynamic = "force-dynamic";

export default async function ApiKeysPage() {
  const customerId = await getCurrentCustomerId();
  const apiKeys = await getApiKeys(customerId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[28px] font-semibold tracking-tight">API Keys</h1>
        <p className="text-sm text-muted-foreground">
          Manage the API keys used to access CloudDesk programmatically.
        </p>
      </div>
      <ApiKeysList apiKeys={apiKeys} />
    </div>
  );
}
