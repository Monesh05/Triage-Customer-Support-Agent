// name: app/support-console/tickets/[id]/page.tsx
// purpose: Support Console Ticket Detail (spec section 26): customer message, detected intent,
//          specialist findings, evidence, resolution, QA result, pending approval, escalation —
//          plus an Agent Trace tab with the full internal execution sequence. Server Component.
// author: CloudDesk Team
// date: 2026-09-24

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { AgentTraceTimeline } from "@/components/console/agent-trace-timeline";
import { EscalationCard, QaResultCard, ResolutionCard } from "@/components/console/resolution-qa-cards";
import { SpecialistFindingsList } from "@/components/console/specialist-findings-list";
import { TicketApprovalStatus } from "@/components/console/ticket-approval-status";
import { TicketOverviewCard } from "@/components/console/ticket-overview-card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { listApprovals } from "@/lib/api/approvals";
import { getTicket, getTicketTrace } from "@/lib/api/tickets";

export const dynamic = "force-dynamic";

export default async function TicketDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [ticket, trace, approvals] = await Promise.all([
    getTicket(id),
    getTicketTrace(id),
    listApprovals(true),
  ]);

  const threadId = trace.runs[0]?.thread_id;
  const ticketApprovals = approvals.filter((approval) => approval.thread_id === threadId);
  const triageRun = trace.runs.find((run) => run.agent_name === "triage");

  return (
    <div className="space-y-6">
      <Link
        href="/support-console/tickets"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" />
        Back to tickets
      </Link>

      <TicketOverviewCard ticket={ticket} triageRun={triageRun} />
      <TicketApprovalStatus approvals={ticketApprovals} />
      <EscalationCard runs={trace.runs} />

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="trace">Agent Trace</TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="space-y-4 pt-2">
          <SpecialistFindingsList runs={trace.runs} />
          <ResolutionCard runs={trace.runs} />
          <QaResultCard runs={trace.runs} />
        </TabsContent>
        <TabsContent value="trace" className="pt-2">
          <AgentTraceTimeline runs={trace.runs} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
