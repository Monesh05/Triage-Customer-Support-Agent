// name: lib/api/types.ts
// purpose: TypeScript types mirroring the CloudDesk backend's Pydantic v2 response/request
//          schemas exactly (see clouddesk/backend/app/schemas/*.py). Kept as a single source of
//          truth for the API contract so every API client function and every component shares
//          the same shapes instead of re-declaring ad-hoc inline types.
// author: CloudDesk Team
// date: 2026-09-24

export type CustomerStatus = "active" | "suspended" | "churned";
export type AccountStatus = "active" | "locked" | "disabled";
export type SubscriptionStatus = "active" | "trialing" | "past_due" | "canceled";
export type PaymentStatus = "succeeded" | "failed" | "pending" | "refunded";
export type PaymentMethod = "card" | "ach" | "paypal" | "wire";
export type InvoiceStatus = "paid" | "open" | "overdue" | "void";
export type ApiKeyStatus = "active" | "revoked" | "expired";
export type IncidentStatus = "investigating" | "identified" | "monitoring" | "resolved";
export type IncidentSeverity = "low" | "medium" | "high" | "critical";
export type TicketStatus = "open" | "in_progress" | "pending_customer" | "resolved" | "closed";
export type TicketPriority = "low" | "medium" | "high" | "urgent";
export type ApprovalStatus = "pending" | "approved" | "rejected";
export type AgentRunStatus = "success" | "failure";
export type ConversationStatusValue =
  | "in_progress"
  | "awaiting_approval"
  | "completed"
  | "escalated"
  | "failed";
export type StepStatus = "done" | "in_progress" | "failed";

export interface Customer {
  id: string;
  name: string;
  email: string;
  organization_id: string;
  created_at: string;
  status: CustomerStatus;
}

export interface Account {
  id: string;
  customer_id: string;
  status: AccountStatus;
  mfa_enabled: boolean;
  failed_login_attempts: number;
  last_login_at: string | null;
  last_login_ip: string | null;
  permissions: string[];
}

export interface Plan {
  id: string;
  name: string;
  price_monthly: number;
  api_rate_limit: number;
  features: string[];
}

export interface Entitlement {
  id: string;
  subscription_id: string;
  granted_plan_id: string;
  granted_api_rate_limit: number;
  granted_features: string[];
  last_synced_at: string;
}

export interface Subscription {
  id: string;
  customer_id: string;
  plan_id: string;
  status: SubscriptionStatus;
  start_date: string;
  renewal_date: string;
  plan: Plan;
  entitlement: Entitlement | null;
}

export interface Payment {
  id: string;
  customer_id: string;
  subscription_id: string;
  amount: number;
  currency: string;
  status: PaymentStatus;
  payment_method: PaymentMethod;
  created_at: string;
  transaction_reference: string;
  billing_period_start: string;
  billing_period_end: string;
}

export interface Invoice {
  id: string;
  customer_id: string;
  subscription_id: string;
  amount: number;
  status: InvoiceStatus;
  issued_at: string;
  due_at: string;
}

export interface UsageRecord {
  id: string;
  customer_id: string;
  api_calls: number;
  period_start: string;
  period_end: string;
}

export interface ApiKey {
  id: string;
  customer_id: string;
  status: ApiKeyStatus;
  created_at: string;
  last_used_at: string | null;
  rate_limit: number;
}

export interface ServiceIncident {
  id: string;
  service_name: string;
  status: IncidentStatus;
  severity: IncidentSeverity;
  started_at: string;
  resolved_at: string | null;
  description: string;
}

export interface SupportTicket {
  id: string;
  customer_id: string;
  subject: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  created_at: string;
  updated_at: string;
  assigned_to: string | null;
}

export interface AgentRun {
  run_id: string;
  ticket_id: string | null;
  thread_id: string;
  agent_name: string;
  start_time: string;
  end_time: string;
  duration_ms: number;
  status: AgentRunStatus;
  input_summary: string | null;
  output_summary: string | null;
  tool_calls: Record<string, unknown>[];
  tool_results: Record<string, unknown>[];
  error: string | null;
  iteration: number | null;
}

export interface TicketTrace {
  ticket_id: string;
  runs: AgentRun[];
}

export interface ApprovalRequest {
  id: string;
  customer_id: string;
  thread_id: string;
  agent_name: string;
  action_description: string;
  amount: number | null;
  payload: Record<string, unknown>;
  status: ApprovalStatus;
  decided_by: string | null;
  decided_at: string | null;
  rejection_reason: string | null;
  refund_request_id: string | null;
  created_at: string;
}

export interface ApprovalDecisionRequest {
  actor: string;
  reason?: string | null;
}

export interface ApprovalDecisionResponse {
  approval_request: ApprovalRequest;
  executed: boolean;
  workflow_resumed: boolean;
  final_response: string | null;
}

export interface ConversationStartRequest {
  customer_id: string;
  message: string;
  conversation_history?: string[] | null;
}

export interface ConversationStartResponse {
  thread_id: string;
  ticket_id: string | null;
  status: ConversationStatusValue;
}

export interface ConversationStep {
  step: string;
  status: StepStatus;
}

export interface ConversationStatus {
  thread_id: string;
  ticket_id: string | null;
  status: ConversationStatusValue;
  steps: ConversationStep[];
  final_response: string | null;
}
