// name: app/login/page.tsx
// purpose: Customer portal login page (Phase 10, spec section 27) — replaces the Phase 9 demo
//          customer-switcher. Shows a short, honest "try it" hint listing a few seeded demo
//          customer emails and their shared demo password, since this is a portfolio/demo app
//          with no real signup flow (spec section 1).
// author: CloudDesk Team
// date: 2026-09-24

import { Cloud } from "lucide-react";

import { LoginForm } from "@/components/auth/login-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DEMO_CUSTOMERS, DEMO_CUSTOMER_PASSWORD } from "@/lib/demo-customers";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-background px-4 py-12">
      <div className="flex items-center gap-2">
        <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Cloud className="size-5" strokeWidth={2.5} />
        </div>
        <span className="text-lg font-semibold">CloudDesk</span>
      </div>

      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Customer sign in</CardTitle>
          <CardDescription>Sign in to view your account, billing, usage, and support history.</CardDescription>
        </CardHeader>
        <CardContent>
          <LoginForm loginEndpoint="/api/auth/login" redirectPath="/dashboard" submitLabel="Sign in" />
        </CardContent>
      </Card>

      <Card className="w-full max-w-sm bg-muted/40">
        <CardHeader>
          <CardTitle className="text-sm">Try it as a demo customer</CardTitle>
          <CardDescription>
            Every seeded customer shares the password <code className="font-mono">{DEMO_CUSTOMER_PASSWORD}</code>.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-1.5 text-xs text-muted-foreground">
          {DEMO_CUSTOMERS.map((demoCustomer) => (
            <div key={demoCustomer.email} className="flex items-center justify-between gap-2">
              <span className="font-mono">{demoCustomer.email}</span>
              <span>{demoCustomer.description}</span>
            </div>
          ))}
        </CardContent>
      </Card>

      <a href="/support-console/login" className="text-xs text-muted-foreground underline underline-offset-4">
        Support Console staff sign in
      </a>
    </div>
  );
}
