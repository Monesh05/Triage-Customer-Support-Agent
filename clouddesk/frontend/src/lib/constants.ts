// name: lib/constants.ts
// purpose: Named constants shared across the frontend (no magic numbers per Phase 9 dev rules).
// author: CloudDesk Team
// date: 2026-09-24

/** How often the support chat polls GET /conversations/{thread_id} while a run is in progress. */
export const CONVERSATION_POLL_INTERVAL_MS: number = 1500;

/** Give up polling a conversation after this many attempts (~3 minutes at the interval above)
 * so a stuck backend run cannot spin the customer's browser forever. */
export const CONVERSATION_MAX_POLL_ATTEMPTS: number = 120;

/** Max characters accepted in one chat message, mirrors the backend's MAX_MESSAGE_LENGTH. */
export const CHAT_MESSAGE_MAX_LENGTH: number = 5000;

/** Cookie name used to persist the selected demo customer (see lib/current-customer.ts). Kept
 * here (not in that server-only module) so client components like CustomerSwitcher can reference
 * it without pulling `next/headers` into the client bundle. */
export const CURRENT_CUSTOMER_COOKIE: string = "clouddesk_customer_id";
