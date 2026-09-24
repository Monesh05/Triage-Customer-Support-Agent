// name: lib/demo-customers.ts
// purpose: Hardcoded seeded demo customer emails (from clouddesk/data/seed), shown on the login
//          page as an honest "try it" hint (Phase 10, spec section 27) — every seeded customer
//          shares the same demo password (see data/seed/builders.py's DEMO_CUSTOMER_PASSWORD).
//          This is purely a UI convenience; it never bypasses real authentication, unlike the
//          Phase 9 cookie-switcher this replaced.
// author: CloudDesk Team
// date: 2026-09-24

export interface DemoCustomer {
  email: string;
  label: string;
  description: string;
}

export const DEMO_CUSTOMER_PASSWORD: string = "demo1234";

export const DEMO_CUSTOMERS: DemoCustomer[] = [
  { email: "acme.normal.free@customer.example", label: "acme Normal Free", description: "Healthy free-tier account" },
  { email: "acme.normal.biz@customer.example", label: "acme Normal Business", description: "Healthy paid account" },
  { email: "acme.dupe@customer.example", label: "acme Duplicate Charge", description: "Has a duplicate payment to dispute" },
  { email: "acme.locked@customer.example", label: "acme Locked Out", description: "Account is locked" },
];
