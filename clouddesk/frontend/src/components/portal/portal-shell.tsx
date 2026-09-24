"use client";

// name: components/portal/portal-shell.tsx
// purpose: The customer portal's app shell: a branded sidebar (desktop) / slide-out sheet
//          (mobile) plus a top bar carrying the demo customer switcher. Wraps server-rendered
//          page content passed in as `children`, so individual pages stay Server Components.
// author: CloudDesk Team
// date: 2026-09-24

import { useState } from "react";
import { Cloud, Menu } from "lucide-react";

import { CustomerSwitcher } from "@/components/portal/customer-switcher";
import { PortalNavLinks } from "@/components/portal/portal-nav-links";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";

function BrandMark() {
  return (
    <div className="flex items-center gap-2 px-2 py-1">
      <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
        <Cloud className="size-4.5" strokeWidth={2.5} />
      </div>
      <div className="leading-tight">
        <p className="text-sm font-semibold">CloudDesk</p>
        <p className="text-[11px] text-muted-foreground">Customer Portal</p>
      </div>
    </div>
  );
}

export function PortalShell({
  customerId,
  children,
}: {
  customerId: string;
  children: React.ReactNode;
}) {
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col gap-6 border-r border-sidebar-border bg-sidebar px-4 py-5 md:flex">
        <BrandMark />
        <PortalNavLinks />
      </aside>

      <Sheet open={isMobileNavOpen} onOpenChange={setIsMobileNavOpen}>
        <SheetContent side="left" className="w-64 gap-6 bg-sidebar px-4 py-5">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <BrandMark />
          <PortalNavLinks onNavigate={() => setIsMobileNavOpen(false)} />
        </SheetContent>
      </Sheet>

      <div className="md:pl-64">
        <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-border bg-background/80 px-4 py-3 backdrop-blur sm:px-6">
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setIsMobileNavOpen(true)}
            aria-label="Open navigation"
          >
            <Menu className="size-5" />
          </Button>
          <div className="md:hidden">
            <BrandMark />
          </div>
          <div className="ml-auto">
            <CustomerSwitcher customerId={customerId} />
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:py-8">{children}</main>
      </div>
    </div>
  );
}
