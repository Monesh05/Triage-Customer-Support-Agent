// name: app/support-console/layout.tsx
// purpose: Layout for the Internal Support Console route group — requires a valid staff session
//          (Phase 10, spec section 27; redirects to /support-console/login otherwise, see
//          lib/current-staff.ts) and wraps every console page in the dark "ops tooling" shell.
// author: CloudDesk Team
// date: 2026-09-24

import { ConsoleShell } from "@/components/console/console-shell";
import { requireStaffSession } from "@/lib/current-staff";

export default async function SupportConsoleLayout({ children }: { children: React.ReactNode }) {
  await requireStaffSession();
  return <ConsoleShell>{children}</ConsoleShell>;
}
