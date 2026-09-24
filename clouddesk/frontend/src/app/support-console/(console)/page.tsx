// name: app/support-console/page.tsx
// purpose: /support-console redirects to its Tickets view, the console's primary landing page.
// author: CloudDesk Team
// date: 2026-09-24

import { redirect } from "next/navigation";

export default function SupportConsoleIndexPage() {
  redirect("/support-console/tickets");
}
