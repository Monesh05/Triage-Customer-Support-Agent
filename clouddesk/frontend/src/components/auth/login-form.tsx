"use client";

// name: components/auth/login-form.tsx
// purpose: Shared email/password login form (Phase 10, spec section 27) used by both the
//          customer portal's /login and the Support Console's /support-console/login — the two
//          pages differ only in which route handler they post to and where a success redirects,
//          both passed in as props so this component stays presentation/flow logic only.
//          2026-09-25 redesign (spec section 13): accepts an optional `prefill` prop so the
//          login page's demo-account cards can fill (and auto-submit) this exact form instead of
//          re-implementing the auth call — clicking a demo card is just a UX shortcut on top of
//          the same POST this form already made.
// author: CloudDesk Team
// date: 2026-09-25

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export interface LoginPrefill {
  email: string;
  password: string;
  /** Bump this on every selection (even re-selecting the same account) so the effect below fires
   * again even when email/password are unchanged from the previous selection. */
  nonce: number;
}

interface LoginFormProps {
  loginEndpoint: string;
  redirectPath: string;
  submitLabel: string;
  prefill?: LoginPrefill | null;
}

export function LoginForm({ loginEndpoint, redirectPath, submitLabel, prefill }: LoginFormProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const lastAppliedNonce = useRef<number | null>(null);

  async function submit(candidateEmail: string, candidatePassword: string) {
    setError(null);
    setIsSubmitting(true);
    try {
      const response = await fetch(loginEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: candidateEmail, password: candidatePassword }),
      });
      if (!response.ok) {
        const body: unknown = await response.json().catch(() => ({}));
        const detail = typeof body === "object" && body !== null && "detail" in body ? String((body as { detail: unknown }).detail) : null;
        setError(detail ?? "Invalid email or password.");
        return;
      }
      router.push(redirectPath);
      router.refresh();
    } catch {
      setError("Could not reach the CloudDesk API. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  useEffect(() => {
    if (!prefill || prefill.nonce === lastAppliedNonce.current) {
      return;
    }
    lastAppliedNonce.current = prefill.nonce;
    setEmail(prefill.email);
    setPassword(prefill.password);
    void submit(prefill.email, prefill.password);
    // Intentionally omitting `submit` from deps: it is stable in behavior (closes over props that
    // don't change), and including it would need a useCallback purely to satisfy this effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefill]);

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        void submit(email, password);
      }}
      className="flex flex-col gap-4"
    >
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </div>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button type="submit" disabled={isSubmitting} className="mt-1">
        {isSubmitting ? "Signing in..." : submitLabel}
      </Button>
    </form>
  );
}
