"use client";

// name: components/portal/customer-switcher.tsx
// purpose: The customer portal's "logged in as" selector — an explicit, visible placeholder for
//          real authentication (Phase 10), not a fake login form. Writes the chosen demo
//          customer id to a cookie the server reads via lib/current-customer.ts, then refreshes
//          the current route so server-rendered pages re-fetch data for the new customer.
// author: CloudDesk Team
// date: 2026-09-24

import { useRouter } from "next/navigation";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CURRENT_CUSTOMER_COOKIE } from "@/lib/constants";
import { DEMO_CUSTOMERS } from "@/lib/demo-customers";

const COOKIE_MAX_AGE_SECONDS: number = 60 * 60 * 24 * 30;

export function CustomerSwitcher({ customerId }: { customerId: string }) {
  const router = useRouter();

  function handleChange(nextCustomerId: string | null) {
    if (!nextCustomerId) return;
    document.cookie = `${CURRENT_CUSTOMER_COOKIE}=${nextCustomerId}; path=/; max-age=${COOKIE_MAX_AGE_SECONDS}`;
    router.refresh();
  }

  return (
    <div className="flex flex-col gap-1">
      <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        Viewing as (demo)
      </span>
      <Select value={customerId} onValueChange={handleChange}>
        <SelectTrigger size="sm" className="w-56 bg-background">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {DEMO_CUSTOMERS.map((demoCustomer) => (
            <SelectItem key={demoCustomer.id} value={demoCustomer.id}>
              <span className="flex flex-col">
                <span>{demoCustomer.label}</span>
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
