"use client";

// name: components/portal/portal-shell.tsx
// purpose: The customer portal's app shell: a branded sidebar (desktop) / slide-out sheet
//          (mobile) plus a top bar carrying the signed-in customer's email and a sign-out button
//          (Phase 10, spec section 27). Wraps server-rendered page content passed in as `children`,
//          so individual pages stay Server Components.
//          2026-09-25 redesign (spec sections 1-2): polished brand mark, a dedicated
//          avatar/email/account-menu block at the bottom of the sidebar behind a subtle divider,
//          and a compact header with a breadcrumb, an inert notifications affordance, and the same
//          account menu. Purely presentational — no auth/routing changes.
// author: CloudDesk Team
// date: 2026-09-25

import { useState } from "react";
import { Bell, Cloud, Menu } from "lucide-react";

import { AccountMenu } from "@/components/portal/account-menu";
import { HeaderBreadcrumb } from "@/components/portal/header-breadcrumb";
import { PortalNavLinks } from "@/components/portal/portal-nav-links";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const CUSTOMER_LOGIN_PATH: string = "/login";

function BrandMark() {
  return (
    <div className="flex items-center gap-2.5 px-2 py-1">
      <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
        <Cloud className="size-4.5" strokeWidth={2.5} />
      </div>
      <div className="leading-tight">
        <p className="text-sm font-semibold tracking-tight">CloudDesk</p>
        <p className="text-[11px] text-muted-foreground">Customer Portal</p>
      </div>
    </div>
  );
}

function NotificationsButton() {
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Button variant="ghost" size="icon" aria-label="Notifications">
            <Bell className="size-4" />
          </Button>
        }
      />
      <TooltipContent>You&apos;re all caught up</TooltipContent>
    </Tooltip>
  );
}

export function PortalShell({
  customerEmail,
  children,
}: {
  customerEmail: string;
  children: React.ReactNode;
}) {
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-sidebar-border bg-sidebar px-3 py-5 md:flex">
        <div className="flex-1 space-y-6">
          <BrandMark />
          <PortalNavLinks />
        </div>
        <Separator className="mb-3 bg-sidebar-border" />
        <AccountMenu email={customerEmail} loginPath={CUSTOMER_LOGIN_PATH} variant="sidebar" />
      </aside>

      <Sheet open={isMobileNavOpen} onOpenChange={setIsMobileNavOpen}>
        <SheetContent side="left" className="flex w-64 flex-col gap-0 bg-sidebar px-3 py-5">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <div className="flex-1 space-y-6">
            <BrandMark />
            <PortalNavLinks onNavigate={() => setIsMobileNavOpen(false)} />
          </div>
          <Separator className="mb-3 bg-sidebar-border" />
          <AccountMenu email={customerEmail} loginPath={CUSTOMER_LOGIN_PATH} variant="sidebar" />
        </SheetContent>
      </Sheet>

      <div className="md:pl-64">
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between gap-4 border-b border-border bg-background/85 px-4 backdrop-blur sm:px-6">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={() => setIsMobileNavOpen(true)}
              aria-label="Open navigation"
            >
              <Menu className="size-5" />
            </Button>
            <div className="hidden md:block">
              <HeaderBreadcrumb />
            </div>
            <div className="md:hidden">
              <BrandMark />
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <NotificationsButton />
            <div className="hidden sm:block">
              <AccountMenu email={customerEmail} loginPath={CUSTOMER_LOGIN_PATH} variant="header" />
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-[1400px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</main>
      </div>
    </div>
  );
}
