"use client";

// name: components/auth/forgot-password-link.tsx
// purpose: The "Forgot password?" affordance spec section 13 asks for. There is no password-reset
//          flow in this backend (it is a seeded-data demo app), so this deliberately does not
//          pretend to send a reset email — it gives an honest, immediate explanation via toast
//          instead of being a dead link that silently does nothing, which the redesign brief's own
//          hygiene guidance (no fake affordances) rules out.
// author: CloudDesk Team
// date: 2026-09-25

import { toast } from "sonner";

export function ForgotPasswordLink() {
  return (
    <button
      type="button"
      onClick={() =>
        toast.info("Password reset isn't available in this demo", {
          description: "Use one of the demo accounts below to sign in instead.",
        })
      }
      className="text-xs font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
    >
      Forgot password?
    </button>
  );
}
