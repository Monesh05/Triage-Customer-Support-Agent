// name: components/console/console-nav-config.ts
// purpose: Shared nav entries for the Internal Support Console shell.
// author: CloudDesk Team
// date: 2026-09-24

import type { LucideIcon } from "lucide-react";
import { ShieldCheck, Ticket } from "lucide-react";

export interface ConsoleNavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const CONSOLE_NAV_ITEMS: ConsoleNavItem[] = [
  { href: "/support-console/tickets", label: "Tickets", icon: Ticket },
  { href: "/support-console/approvals", label: "Approval Queue", icon: ShieldCheck },
];
