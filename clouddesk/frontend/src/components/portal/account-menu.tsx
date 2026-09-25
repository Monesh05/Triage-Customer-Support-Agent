"use client";

// name: components/portal/account-menu.tsx
// purpose: The customer portal's account menu (2026-09-25 redesign, spec sections 1-2): a small
//          avatar + email trigger, used both at the bottom of the sidebar (spec section 1's "user/
//          account section") and in the top header (spec section 2's "account dropdown"). Opens a
//          dropdown with the signed-in email and a sign-out action, reusing the exact sign-out
//          flow from components/shared/logout-button.tsx so this never diverges from the real
//          auth/logout behavior.
// author: CloudDesk Team
// date: 2026-09-25

import { LogOut } from "lucide-react";

import { useLogout } from "@/components/shared/logout-button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

function initialsFor(email: string): string {
  const namePart = email.split("@")[0] ?? email;
  const segments = namePart.split(/[.\-_]/).filter(Boolean);
  const initials = segments.slice(0, 2).map((segment) => segment[0]?.toUpperCase() ?? "");
  return initials.join("") || email.slice(0, 2).toUpperCase();
}

export function AccountMenu({
  email,
  loginPath,
  variant = "sidebar",
}: {
  email: string;
  loginPath: string;
  variant?: "sidebar" | "header";
}) {
  const { logout, isLoggingOut } = useLogout(loginPath);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          "flex w-full items-center gap-2.5 rounded-lg text-left outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring/50",
          variant === "sidebar"
            ? "px-2 py-1.5 hover:bg-sidebar-accent/70"
            : "rounded-full p-0.5 hover:bg-muted"
        )}
        aria-label="Account menu"
      >
        <Avatar size="sm" className="shrink-0">
          <AvatarFallback className="bg-primary/10 text-[11px] font-semibold text-primary">
            {initialsFor(email)}
          </AvatarFallback>
        </Avatar>
        {variant === "sidebar" ? (
          <span className="min-w-0 flex-1 truncate text-xs font-medium text-sidebar-foreground">{email}</span>
        ) : null}
      </DropdownMenuTrigger>
      <DropdownMenuContent align={variant === "sidebar" ? "start" : "end"} className="w-56">
        <DropdownMenuLabel className="truncate font-normal text-foreground">{email}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          variant="destructive"
          disabled={isLoggingOut}
          onClick={(event) => {
            event.preventDefault();
            void logout();
          }}
        >
          <LogOut className="size-4" />
          {isLoggingOut ? "Signing out..." : "Sign out"}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
