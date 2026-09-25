"use client";

// name: components/portal/portal-nav-links.tsx
// purpose: The actual list of nav links (with active-route highlighting), rendered by both the
//          desktop sidebar and the mobile nav sheet. Split out because active-state needs
//          usePathname, which forces this piece (only) to be a client component.
//          2026-09-25 redesign (spec section 1): tighter active/hover states, a left active-rail
//          instead of a filled pill (less "pill-heavy"), and AI Support — the product's core
//          feature — gets a subtly accented icon so it reads as visually important without
//          looking like an ad.
// author: CloudDesk Team
// date: 2026-09-25

import Link from "next/link";
import { usePathname } from "next/navigation";

import { PORTAL_NAV_ITEMS } from "@/components/portal/nav-config";
import { cn } from "@/lib/utils";

const AI_SUPPORT_HREF: string = "/support";

export function PortalNavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary" className="flex flex-col gap-0.5">
      {PORTAL_NAV_ITEMS.map((item) => {
        const isActive = pathname.startsWith(item.href);
        const isAiSupport = item.href === AI_SUPPORT_HREF;
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              "group relative flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-150",
              isActive
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-sidebar-foreground/65 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
            )}
          >
            <span
              className={cn(
                "absolute inset-y-1 left-0 w-0.5 rounded-full bg-primary transition-opacity",
                isActive ? "opacity-100" : "opacity-0"
              )}
              aria-hidden
            />
            <Icon
              className={cn("size-4", isAiSupport && !isActive && "text-primary/70")}
              strokeWidth={2}
            />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
