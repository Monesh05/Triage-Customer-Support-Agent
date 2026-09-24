// name: lib/api/tickets.ts
// purpose: Typed client functions for support tickets and their agent-execution trace, used by
//          the Internal Support Console (spec section 26).
// author: CloudDesk Team
// date: 2026-09-24

import { apiRequest } from "@/lib/api/client";
import type { SupportTicket, TicketTrace } from "@/lib/api/types";

export function listAllTickets(): Promise<SupportTicket[]> {
  return apiRequest<SupportTicket[]>("/tickets");
}

export function getTicket(ticketId: string): Promise<SupportTicket> {
  return apiRequest<SupportTicket>(`/tickets/${ticketId}`);
}

export function getTicketTrace(ticketId: string): Promise<TicketTrace> {
  return apiRequest<TicketTrace>(`/tickets/${ticketId}/trace`);
}
