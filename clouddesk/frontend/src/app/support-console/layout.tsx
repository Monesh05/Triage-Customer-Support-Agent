// name: app/support-console/layout.tsx
// purpose: Layout for the Internal Support Console route group — wraps every console page in the
//          dark "ops tooling" shell.
// author: CloudDesk Team
// date: 2026-09-24

import { ConsoleShell } from "@/components/console/console-shell";

export default function SupportConsoleLayout({ children }: { children: React.ReactNode }) {
  return <ConsoleShell>{children}</ConsoleShell>;
}
