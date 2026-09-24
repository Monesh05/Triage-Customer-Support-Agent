"use client";

// name: components/portal/portal-nav-links.tsx
// purpose: The actual list of nav links (with active-route highlighting), rendered by both the
//          desktop sidebar and the mobile nav sheet. Split out because active-state needs
//          usePathname, which forces this piece (only) to be a client component.
// author: CloudDesk Team
// date: 2026-09-24

import Link from "next/link";
import { usePathname } from "next/navigation";

import { PORTAL_NAV_ITEMS } from "@/components/portal/nav-config";
import { cn } from "@/lib/utils";

export function PortalNavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col gap-1">
      {PORTAL_NAV_ITEMS.map((item) => {
        const isActive = pathname.startsWith(item.href);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
            )}
          >
            <Icon className="size-4" strokeWidth={2} />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
