// name: lib/api/customers.ts
// purpose: Typed client functions for the /customers endpoints.
// author: CloudDesk Team
// date: 2026-09-24

import { apiRequest } from "@/lib/api/client";
import type { Customer, SupportTicket } from "@/lib/api/types";

export function getCustomer(customerId: string): Promise<Customer> {
  return apiRequest<Customer>(`/customers/${customerId}`);
}

export function getCustomerTickets(customerId: string): Promise<SupportTicket[]> {
  return apiRequest<SupportTicket[]>(`/customers/${customerId}/tickets`);
}
