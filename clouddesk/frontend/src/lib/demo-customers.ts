// name: lib/demo-customers.ts
// purpose: Hardcoded seeded demo customers (from clouddesk/data/seed) used as the customer
//          portal's "logged in as" selector. There is no authentication system yet (that is
//          Phase 10) — this is an explicit, clearly-labeled placeholder for it, kept in one file
//          so swapping it for a real session/auth lookup later touches this module only, not
//          every page that currently reads a customer id.
// author: CloudDesk Team
// date: 2026-09-24

export interface DemoCustomer {
  id: string;
  label: string;
  description: string;
}

/** Seeded customers from the Phase 1-8 dev database (docker compose postgres, port 5433). IDs
 * are stable across restarts because they come from the deterministic seed script. */
export const DEMO_CUSTOMERS: DemoCustomer[] = [
  {
    id: "6e48d7b8-7de2-421a-9c7d-c9aa50eaae58",
    label: "acme Normal Free",
    description: "Healthy free-tier account",
  },
  {
    id: "db6e0195-91a5-4b76-ac33-d55ea5165a74",
    label: "acme Normal Business",
    description: "Healthy paid account",
  },
  {
    id: "8f63648a-fe1e-430d-9980-8b4f1a3693be",
    label: "acme Duplicate Charge",
    description: "Has a duplicate payment to dispute",
  },
  {
    id: "51d1d54d-b0fe-4d46-91f8-9b8240ac5843",
    label: "acme Failed Payment",
    description: "Most recent payment failed",
  },
  {
    id: "bc7f87e2-138f-4679-b7fa-a63d833eafed",
    label: "acme Pending Payment",
    description: "Payment currently pending",
  },
  {
    id: "ccf4096c-e08f-4a21-a363-9743357e0006",
    label: "acme Stale Entitlement",
    description: "Entitlements out of sync with plan",
  },
  {
    id: "d9819207-9c1c-48fe-a740-f76aa1c5bd43",
    label: "acme Locked Out",
    description: "Account is locked",
  },
  {
    id: "dfbf4bb4-c82b-48c5-b7a8-14366de30c3b",
    label: "acme Heavy Legit User",
    description: "High legitimate API usage",
  },
];

export const DEFAULT_DEMO_CUSTOMER_ID: string = DEMO_CUSTOMERS[0].id;
