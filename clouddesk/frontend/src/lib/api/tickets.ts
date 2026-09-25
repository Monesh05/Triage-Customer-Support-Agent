// name: lib/api/tickets.ts
// purpose: Typed client functions for support tickets: the Internal Support Console's
//          cross-customer list and raw agent-execution trace (spec section 26), plus (post-launch,
//          2026-09-25) the customer portal's customer-safe ticket summary and self-service close.
// author: CloudDesk Team
// date: 2026-09-25

import { apiRequest } from "@/lib/api/client";
import type { SupportTicket, TicketSummary, TicketTrace } from "@/lib/api/types";

export function listAllTickets(): Promise<SupportTicket[]> {
  return apiRequest<SupportTicket[]>("/tickets");
}

export function getTicket(ticketId: string): Promise<SupportTicket> {
  return apiRequest<SupportTicket>(`/tickets/${ticketId}`);
}

export function getTicketTrace(ticketId: string): Promise<TicketTrace> {
  return apiRequest<TicketTrace>(`/tickets/${ticketId}/trace`);
}

/** The customer-safe outcome view for one ticket (never raw agent tool_calls/tool_results). */
export function getTicketSummary(ticketId: string): Promise<TicketSummary> {
  return apiRequest<TicketSummary>(`/tickets/${ticketId}/summary`);
}

/** Close a ticket at its own customer's request. Throws `ApiError` (status 409) if it is already
 * closed, or (status 403) if the caller does not own it. */
export function closeTicket(ticketId: string): Promise<SupportTicket> {
  return apiRequest<SupportTicket>(`/tickets/${ticketId}/close`, { method: "POST" });
}
