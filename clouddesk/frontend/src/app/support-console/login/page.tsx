// name: app/support-console/login/page.tsx
// purpose: Support Console staff login page (Phase 10, spec section 27) — a distinct login mode
//          from the customer portal's /login, posting to the staff-only backend endpoint and
//          issuing a token with `role: "staff"`. Deliberately outside the
//          app/support-console/(console) route group so it is NOT gated by that group's
//          `requireStaffSession` layout check (which would otherwise redirect back here forever).
// author: CloudDesk Team
// date: 2026-09-24

import { TerminalSquare } from "lucide-react";

import { LoginForm } from "@/components/auth/login-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const STAFF_DEMO_EMAIL: string = "staff@clouddesk.example";
const STAFF_DEMO_PASSWORD: string = "staff1234";

export default function StaffLoginPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-background px-4 py-12">
      <div className="flex items-center gap-2">
        <div className="flex size-9 items-center justify-center rounded-lg bg-slate-800 text-cyan-400">
          <TerminalSquare className="size-5" strokeWidth={2.5} />
        </div>
        <span className="text-lg font-semibold">CloudDesk Support Console</span>
      </div>

      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Staff sign in</CardTitle>
          <CardDescription>Internal use only. Sign in with your support-console staff account.</CardDescription>
        </CardHeader>
        <CardContent>
          <LoginForm
            loginEndpoint="/api/auth/staff-login"
            redirectPath="/support-console"
            submitLabel="Sign in"
          />
        </CardContent>
      </Card>

      <Card className="w-full max-w-sm bg-muted/40">
        <CardHeader>
          <CardTitle className="text-sm">Demo staff account</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-1 text-xs text-muted-foreground">
          <span className="font-mono">{STAFF_DEMO_EMAIL}</span>
          <span className="font-mono">password: {STAFF_DEMO_PASSWORD}</span>
        </CardContent>
      </Card>

      <a href="/login" className="text-xs text-muted-foreground underline underline-offset-4">
        Customer sign in
      </a>
    </div>
  );
}
