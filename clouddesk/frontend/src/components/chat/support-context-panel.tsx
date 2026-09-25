// name: components/chat/support-context-panel.tsx
// purpose: AI Support's context panel (spec section 10) — the single highest-value piece of the
//          redesign for the "this is a real agentic system" demo requirement (spec section 19): it
//          shows the customer/account/usage/ticket context the agent actually has access to via
//          its own tools, built entirely from data the /support page already fetches server-side
//          (Customer, Account, Subscription, UsageRecord, SupportTicket) — nothing here is
//          fabricated or hits a new endpoint. Desktop renders it as a fixed right rail; mobile gets
//          the identical content behind a "View account context" sheet trigger (spec section 16).
// author: CloudDesk Team
// date: 2026-09-25

import { AlertCircle, KeyRound, Layers, Mail, ShieldCheck, Ticket } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/status-badge";
import type { Account, Subscription, SupportTicket, UsageRecord } from "@/lib/api/types";

const OPEN_TICKET_STATUSES: ReadonlySet<string> = new Set(["open", "in_progress", "pending_customer"]);
const MAX_RECENT_ISSUES: number = 3;

interface ContextRowProps {
  icon: typeof Mail;
  label: string;
  children: React.ReactNode;
}

function ContextRow({ icon: Icon, label, children }: ContextRowProps) {
  return (
    <div className="flex items-start gap-2.5">
      <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" strokeWidth={2} />
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <div className="text-sm font-medium">{children}</div>
      </div>
    </div>
  );
}

export function SupportContextPanel({
  customerEmail,
  account,
  subscription,
  latestUsage,
  tickets,
}: {
  customerEmail: string;
  account: Account;
  subscription: Subscription | undefined;
  latestUsage: UsageRecord | undefined;
  tickets: SupportTicket[];
}) {
  const openTickets = tickets.filter((ticket) => OPEN_TICKET_STATUSES.has(ticket.status));
  const recentIssues = openTickets.slice(0, MAX_RECENT_ISSUES);

  return (
    <Card className="border-border/70">
      <CardHeader>
        <CardTitle className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Account context
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <ContextRow icon={Mail} label="Customer">
          <span className="break-all">{customerEmail}</span>
        </ContextRow>

        <ContextRow icon={Layers} label="Account">
          {subscription ? subscription.plan.name : "No active plan"}
        </ContextRow>

        <ContextRow icon={ShieldCheck} label="Status">
          <StatusBadge status={account.status} />
        </ContextRow>

        <ContextRow icon={KeyRound} label="API usage">
          {latestUsage && subscription
            ? `${latestUsage.api_calls.toLocaleString()} / ${subscription.plan.api_rate_limit.toLocaleString()}`
            : "No usage recorded"}
        </ContextRow>

        <ContextRow icon={Ticket} label="Open tickets">
          {openTickets.length}
        </ContextRow>

        {recentIssues.length > 0 ? (
          <div className="space-y-1.5 border-t border-border pt-3.5">
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <AlertCircle className="size-3.5" />
              Recent issues
            </p>
            <ul className="space-y-1">
              {recentIssues.map((ticket) => (
                <li key={ticket.id} className="truncate text-sm text-foreground">
                  · {ticket.subject}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
