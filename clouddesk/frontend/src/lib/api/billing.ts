// name: lib/api/billing.ts
// purpose: Typed client functions for the billing-domain endpoints used by the customer portal's
//          /billing and /usage pages: accounts, subscriptions, payments, invoices, usage,
//          incidents. Grouped in one module since they are all simple "list by customer" reads.
// author: CloudDesk Team
// date: 2026-09-24

import { apiRequest } from "@/lib/api/client";
import type {
  Account,
  ApiKey,
  Invoice,
  Payment,
  ServiceIncident,
  Subscription,
  UsageRecord,
} from "@/lib/api/types";

export function getAccount(customerId: string): Promise<Account> {
  return apiRequest<Account>(`/accounts/${customerId}`);
}

export function getSubscriptions(customerId: string): Promise<Subscription[]> {
  return apiRequest<Subscription[]>(`/subscriptions/${customerId}`);
}

export function getPayments(customerId: string): Promise<Payment[]> {
  return apiRequest<Payment[]>(`/payments/${customerId}`);
}

export function getInvoices(customerId: string): Promise<Invoice[]> {
  return apiRequest<Invoice[]>(`/invoices/${customerId}`);
}

export function getUsage(customerId: string): Promise<UsageRecord[]> {
  return apiRequest<UsageRecord[]>(`/usage/${customerId}`);
}

export function getApiKeys(customerId: string): Promise<ApiKey[]> {
  return apiRequest<ApiKey[]>(`/api-keys/${customerId}`);
}

export function getIncidents(): Promise<ServiceIncident[]> {
  return apiRequest<ServiceIncident[]>("/incidents");
}
