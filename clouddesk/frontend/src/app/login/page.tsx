// name: app/login/page.tsx
// purpose: Customer portal login page (spec section 13) — a minimal, centered SaaS auth screen.
//          2026-09-25 redesign: demo accounts are now selectable cards (components/auth/
//          demo-account-picker.tsx) that fill and submit the real sign-in form instead of a plain
//          list of credentials to retype, and a "Forgot password?" affordance gives an honest
//          explanation rather than pretending to send a reset email this backend cannot send.
// author: CloudDesk Team
// date: 2026-09-25

import { Cloud } from "lucide-react";

import { DemoAccountPicker } from "@/components/auth/demo-account-picker";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-background px-4 py-12">
      <div className="flex items-center gap-2">
        <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Cloud className="size-5" strokeWidth={2.5} />
        </div>
        <span className="text-lg font-semibold tracking-tight">CloudDesk</span>
      </div>

      <Card className="w-full max-w-sm border-border/70 shadow-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-xl">Welcome back</CardTitle>
          <CardDescription>Sign in to your CloudDesk account</CardDescription>
        </CardHeader>
        <CardContent>
          <DemoAccountPicker />
        </CardContent>
      </Card>

      <a href="/support-console/login" className="text-xs text-muted-foreground underline underline-offset-4">
        Support Console staff sign in
      </a>
    </div>
  );
}
