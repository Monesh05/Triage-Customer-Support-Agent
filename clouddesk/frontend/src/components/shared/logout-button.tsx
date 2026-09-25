"use client";

// name: components/shared/logout-button.tsx
// purpose: Shared logout affordance for both the customer portal and the Support Console (Phase
//          10, spec section 27) — clears the httpOnly auth cookie via app/api/auth/logout, then
//          sends the user back to the given login route. The underlying `useLogout` hook is
//          exported separately (2026-09-25 redesign) so the new sidebar account menu
//          (components/portal/account-menu.tsx) can trigger the exact same sign-out flow from
//          inside a dropdown item instead of duplicating the fetch/redirect logic.
// author: CloudDesk Team
// date: 2026-09-25

import { useState } from "react";
import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";

export function useLogout(loginPath: string) {
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  async function logout() {
    setIsLoggingOut(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } finally {
      router.push(loginPath);
      router.refresh();
    }
  }

  return { logout, isLoggingOut };
}

export function LogoutButton({ loginPath }: { loginPath: string }) {
  const { logout, isLoggingOut } = useLogout(loginPath);

  return (
    <Button variant="ghost" size="sm" onClick={logout} disabled={isLoggingOut} className="gap-1.5">
      <LogOut className="size-4" />
      {isLoggingOut ? "Signing out..." : "Sign out"}
    </Button>
  );
}
