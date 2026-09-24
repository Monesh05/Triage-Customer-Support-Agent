"use client";

// name: components/auth/login-form.tsx
// purpose: Shared email/password login form (Phase 10, spec section 27) used by both the
//          customer portal's /login and the Support Console's /support-console/login — the two
//          pages differ only in which route handler they post to and where a success redirects,
//          both passed in as props so this component stays presentation/flow logic only.
// author: CloudDesk Team
// date: 2026-09-24

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface LoginFormProps {
  loginEndpoint: string;
  redirectPath: string;
  submitLabel: string;
}

export function LoginForm({ loginEndpoint, redirectPath, submitLabel }: LoginFormProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const response = await fetch(loginEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
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

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
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
