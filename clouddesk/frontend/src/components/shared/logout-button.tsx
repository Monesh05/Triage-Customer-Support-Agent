"use client";

// name: components/shared/logout-button.tsx
// purpose: Shared logout affordance for both the customer portal and the Support Console (Phase
//          10, spec section 27) — clears the httpOnly auth cookie via app/api/auth/logout, then
//          sends the user back to the given login route.
// author: CloudDesk Team
// date: 2026-09-24

import { useState } from "react";
import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";

export function LogoutButton({ loginPath }: { loginPath: string }) {
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  async function handleLogout() {
    setIsLoggingOut(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } finally {
      router.push(loginPath);
      router.refresh();
    }
  }

  return (
    <Button variant="ghost" size="sm" onClick={handleLogout} disabled={isLoggingOut} className="gap-1.5">
      <LogOut className="size-4" />
      {isLoggingOut ? "Signing out..." : "Sign out"}
    </Button>
  );
}
