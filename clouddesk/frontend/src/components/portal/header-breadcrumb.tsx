"use client";

// name: components/portal/header-breadcrumb.tsx
// purpose: Compact page-context label for the top header (spec section 2: "Breadcrumb/page
//          context where useful"). Derived purely from the current route against the existing nav
//          config — no new data fetching, no routing changes.
// author: CloudDesk Team
// date: 2026-09-25

import { usePathname } from "next/navigation";

import { PORTAL_NAV_ITEMS } from "@/components/portal/nav-config";

export function HeaderBreadcrumb() {
  const pathname = usePathname();
  const activeItem = PORTAL_NAV_ITEMS.find((item) => pathname.startsWith(item.href));

  if (!activeItem) {
    return null;
  }

  return (
    <p className="text-sm font-medium text-foreground">
      <span className="text-muted-foreground">CloudDesk</span>
      <span className="mx-1.5 text-muted-foreground/50">/</span>
      {activeItem.label}
    </p>
  );
}
