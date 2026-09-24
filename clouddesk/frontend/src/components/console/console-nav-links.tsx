"use client";

// name: components/console/console-nav-links.tsx
// purpose: Console sidebar nav links with active-route highlighting, styled with the dedicated
//          --console-* tokens so the console reads as distinct "ops tooling" regardless of the
//          site-wide light/dark theme.
// author: CloudDesk Team
// date: 2026-09-24

import Link from "next/link";
import { usePathname } from "next/navigation";

import { CONSOLE_NAV_ITEMS } from "@/components/console/console-nav-config";
import { cn } from "@/lib/utils";

export function ConsoleNavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col gap-1">
      {CONSOLE_NAV_ITEMS.map((item) => {
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
                ? "bg-console-active text-console-fg"
                : "text-console-muted hover:bg-console-active/60 hover:text-console-fg"
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
