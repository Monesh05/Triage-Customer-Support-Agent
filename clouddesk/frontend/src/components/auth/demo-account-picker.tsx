"use client";

// name: components/auth/demo-account-picker.tsx
// purpose: Owns the shared prefill state between the sign-in form and the "Try a demo account"
//          cards (spec section 13): clicking a card fills and submits the exact same LoginForm
//          used for a manual sign-in — no separate/duplicate auth path — instead of the previous
//          design that only printed the demo emails and password as plain text for the customer to
//          retype by hand.
// author: CloudDesk Team
// date: 2026-09-25

import { useState } from "react";

import { ForgotPasswordLink } from "@/components/auth/forgot-password-link";
import { LoginForm, type LoginPrefill } from "@/components/auth/login-form";
import { DEMO_CUSTOMER_PASSWORD, DEMO_CUSTOMERS } from "@/lib/demo-customers";

export function DemoAccountPicker() {
  const [prefill, setPrefill] = useState<LoginPrefill | null>(null);

  return (
    <div className="flex w-full max-w-sm flex-col gap-6">
      <div className="space-y-3">
        <LoginForm
          loginEndpoint="/api/auth/login"
          redirectPath="/dashboard"
          submitLabel="Sign in"
          prefill={prefill}
        />
        <div className="flex justify-end">
          <ForgotPasswordLink />
        </div>
      </div>

      <div className="space-y-2.5">
        <p className="text-center text-xs font-medium text-muted-foreground">Try a demo account</p>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {DEMO_CUSTOMERS.map((demoCustomer) => (
            <button
              key={demoCustomer.email}
              type="button"
              onClick={() =>
                setPrefill({
                  email: demoCustomer.email,
                  password: DEMO_CUSTOMER_PASSWORD,
                  nonce: Date.now(),
                })
              }
              className="flex flex-col items-start gap-0.5 rounded-lg border border-border bg-card px-3 py-2.5 text-left transition-colors hover:border-primary/40 hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
            >
              <span className="text-sm font-medium">{demoCustomer.label}</span>
              <span className="text-xs text-muted-foreground">{demoCustomer.description}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
