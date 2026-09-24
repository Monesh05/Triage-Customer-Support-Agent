"use client";

// name: components/console/console-shell.tsx
// purpose: The Internal Support Console's app shell — a dark slate sidebar with a cyan accent,
//          deliberately distinct from the customer portal's airy indigo look (spec section 26:
//          this is internal ops tooling, not the customer-facing product).
// author: CloudDesk Team
// date: 2026-09-24

import { useState } from "react";
import { Menu, TerminalSquare } from "lucide-react";

import { ConsoleNavLinks } from "@/components/console/console-nav-links";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";

function ConsoleBrandMark() {
  return (
    <div className="flex items-center gap-2 px-2 py-1">
      <div className="flex size-8 items-center justify-center rounded-lg bg-console-accent/20 text-console-accent">
        <TerminalSquare className="size-4.5" strokeWidth={2.5} />
      </div>
      <div className="leading-tight">
        <p className="text-sm font-semibold text-console-fg">CloudDesk</p>
        <p className="text-[11px] text-console-muted">Support Console</p>
      </div>
    </div>
  );
}

export function ConsoleShell({ children }: { children: React.ReactNode }) {
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col gap-6 border-r border-console-border bg-console-bg px-4 py-5 md:flex">
        <ConsoleBrandMark />
        <ConsoleNavLinks />
      </aside>

      <Sheet open={isMobileNavOpen} onOpenChange={setIsMobileNavOpen}>
        <SheetContent side="left" className="w-64 gap-6 border-console-border bg-console-bg px-4 py-5">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <ConsoleBrandMark />
          <ConsoleNavLinks onNavigate={() => setIsMobileNavOpen(false)} />
        </SheetContent>
      </Sheet>

      <div className="md:pl-64">
        <header className="sticky top-0 z-20 flex items-center gap-4 border-b border-border bg-background/80 px-4 py-3 backdrop-blur sm:px-6">
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setIsMobileNavOpen(true)}
            aria-label="Open navigation"
          >
            <Menu className="size-5" />
          </Button>
          <p className="text-sm font-medium text-muted-foreground">Internal use only</p>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:py-8">{children}</main>
      </div>
    </div>
  );
}
