// name: app/page.tsx
// purpose: Root route — redirects to the customer portal dashboard, the app's real landing page.
// author: CloudDesk Team
// date: 2026-09-24

import { redirect } from "next/navigation";

export default function RootPage() {
  redirect("/dashboard");
}
