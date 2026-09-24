// name: components/portal/nav-config.ts
// purpose: Single source of truth for the customer portal's sidebar navigation entries, shared
//          by the desktop sidebar and the mobile nav sheet so they never drift apart.
// author: CloudDesk Team
// date: 2026-09-24

import type { LucideIcon } from "lucide-react";
import { CreditCard, Gauge, KeyRound, LayoutDashboard, MessageCircle } from "lucide-react";

export interface PortalNavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const PORTAL_NAV_ITEMS: PortalNavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/billing", label: "Billing", icon: CreditCard },
  { href: "/usage", label: "Usage", icon: Gauge },
  { href: "/api", label: "API Keys", icon: KeyRound },
  { href: "/support", label: "AI Support", icon: MessageCircle },
];
