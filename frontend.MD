I want you to significantly improve the frontend/UI of my simulated SaaS customer support application.

IMPORTANT:
- Do NOT change the existing backend logic, APIs, database, authentication, routing, agent logic, or functionality.
- Do NOT remove any existing features.
- This is a frontend/UI redesign only.
- Keep all existing data and interactions working.
- Make the application feel like a real production SaaS product, not a demo/mockup.
- Maintain the existing overall information architecture: Dashboard, Billing, Usage, API Keys, and AI Support.
- Make the UI responsive for desktop, tablet, and mobile.
- Do not over-engineer the design or add unnecessary animations.

DESIGN DIRECTION

Use a modern B2B SaaS aesthetic inspired by products such as Linear, Stripe, Intercom, Vercel, and modern developer platforms.

The design should feel:
- Premium
- Minimal
- Professional
- Trustworthy
- Technical
- Clean
- Modern
- Easy to scan

Use:
- A neutral/light background
- White cards
- Subtle borders
- Very light shadows
- Consistent border radius
- Dark charcoal text
- Blue as the primary accent
- Green/yellow/red only for status and severity
- Excellent typography hierarchy
- More whitespace than the current design
- Consistent spacing throughout the application

Avoid:
- Excessive rounded/pill elements
- Huge empty spaces
- Overly decorative gradients
- Excessive colors
- Generic AI-looking UI
- Excessive animations
- Changing the product into a completely different visual identity

--------------------------------------------------
1. GLOBAL LAYOUT
--------------------------------------------------

Redesign the overall application shell.

Desktop:
- Fixed left sidebar around 240–260px wide.
- Main content should have a comfortable max-width around 1200–1400px.
- Use consistent 24–32px page padding.
- Keep the top area clean and compact.
- Improve alignment between sidebar and page content.

Sidebar:
- Make the CloudDesk logo/product identity more polished.
- Improve icon alignment and sizing.
- Use clear active-state styling.
- Add subtle hover states.
- Improve typography hierarchy.
- Group navigation logically if appropriate.

Navigation:

Dashboard
Billing
Usage
API Keys
AI Support

Make AI Support visually important because it is the core feature of the product, but don't make it look like an advertisement.

At the bottom of the sidebar, add a small user/account section containing:
- Avatar
- User email/name
- Account menu
- Sign out

Use a subtle divider before this section.

--------------------------------------------------
2. TOP HEADER
--------------------------------------------------

Create a polished SaaS header.

Include:
- Breadcrumb/page context where useful
- User account information
- Small avatar
- Account dropdown
- Optional notification icon

Keep the header compact.

Avoid wasting vertical space.

--------------------------------------------------
3. DASHBOARD
--------------------------------------------------

Redesign the dashboard to immediately communicate account health.

Top section:

"Welcome back, Acme"

Instead of:
"Welcome back, acme Duplicate Charge"

Use the actual issue/customer context in a more structured way.

Add a compact account health/incident summary.

For example:

Account health
● 2 issues require attention

Then show the existing issues in a clean incident/alert list.

Each issue should have:
- Category
- Status
- Severity
- Short description
- Optional "View details" action

Example:

Authentication
Investigating
Medium
Intermittent login failures affecting a subset of customers.

API
Monitoring
High
Elevated 5xx error rates on the public API gateway.

Billing
Identified
Low
Invoice generation delayed by up to 6 hours.

Make severity visually distinct but subtle.

Use:
- Red/orange for high severity
- Yellow/orange for medium
- Neutral/green for low/resolved

Do not use huge warning boxes.

--------------------------------------------------
4. DASHBOARD METRICS
--------------------------------------------------

Improve the current metric cards.

Use 3–4 compact cards:

API Usage
15,000 / 50,000
30% used
+ small trend indicator if data exists

Current Plan
Pro
$49/month

Account Status
Active
Healthy account

Next Invoice
Oct 15, 2026
$49.00

Each card should have:
- Small label
- Large primary value
- Secondary context
- Small icon
- Consistent height

Make these feel like real SaaS analytics cards.

--------------------------------------------------
5. RECENT ACTIVITY
--------------------------------------------------

Redesign Recent Activity into a proper activity feed.

Example:

Recent activity

Sep 25
AI Support ticket created
"Does the Pro plan include API access?"

Sep 25
Billing issue detected
"Possible duplicate charge detected."

Each item should have:
- Icon
- Timestamp
- Event title
- Short description
- Status badge

Make this section visually easier to scan.

--------------------------------------------------
6. BILLING PAGE
--------------------------------------------------

The billing page should feel similar to Stripe's billing UI.

Create clear sections:

Current plan
----------------
Pro
$49/month
Renews Oct 15, 2026

[Manage plan]

Features:
✓ Community support
✓ Priority email support
✓ API access

Payment history
----------------

Use a polished table with:
Date
Description
Amount
Payment method
Status
Reference

Improve the duplicate-charge warning.

Instead of making it look like a generic alert, create a clear billing incident component:

Potential duplicate charge detected

Two successful $49 charges were recorded on Sep 1, 2026.

[Investigate with AI Support]

The transaction references should remain available but be visually secondary.

Invoices should use a proper table/list layout.

--------------------------------------------------
7. USAGE PAGE
--------------------------------------------------

Make this page look like a real developer SaaS analytics page.

Top section:

API usage
15,000 / 50,000 calls

30% of monthly limit

Create a more polished progress bar.

Then add supporting metrics if the existing data allows:

Current usage
15,000

Monthly limit
50,000

Remaining
35,000

Reset date
Sep 30, 2026

If actual historical data doesn't exist, don't fabricate charts/data.

Do not add fake metrics just for visual purposes.

--------------------------------------------------
8. API KEYS PAGE
--------------------------------------------------

Make this page look like a professional developer platform.

Include:
API Keys

Create and manage API keys used to access the CloudDesk API.

Show keys in a secure table/list.

Example:

Production API Key
••••••••••••••••••••••abcd

Created
Sep 1, 2026

Last used
Today

[Reveal] [Copy] [Revoke]

Add a clear:

+ Create API key

button.

Never expose full API keys in the UI.

--------------------------------------------------
9. AI SUPPORT PAGE — MOST IMPORTANT
--------------------------------------------------

This is the centerpiece of the application.

Make this page feel like a production-grade AI customer support platform.

Current screen has a large empty chat area.

Reduce unnecessary empty space and make the chat experience feel much more polished.

Layout:

--------------------------------------------------
AI Support

AI-powered support for billing, account, and technical issues.

[Conversation area]      [Ticket/Context panel]
--------------------------------------------------

Main chat area:

Top:
CloudDesk AI Support
● Online

Conversation messages should use clean chat bubbles/cards.

User:
"I was charged twice after upgrading to Pro."

AI:
"I can see two successful $49 charges on September 1. I can help investigate whether this is a duplicate payment."

The AI response should visually communicate:
- What it found
- Which tools/data it used
- What action it recommends

For example:

I found 2 successful transactions:

$49.00 — Sep 1 — TXN_...
$49.00 — Sep 1 — TXN_...

This appears to match the duplicate-charge issue associated with your account.

[View billing details]

Do not make the AI interface overly futuristic.

The goal is trustworthy enterprise AI, not a chatbot gimmick.

--------------------------------------------------
10. AI SUPPORT CONTEXT PANEL
--------------------------------------------------

On desktop, add a right-side context panel.

Show:

Customer
acme.dupe@customer.example

Account
Pro

Status
Active

API usage
15,000 / 50,000

Open tickets
2

Recent issues
- Duplicate payment
- API 5xx errors

This demonstrates that the AI agent has access to customer context.

This is extremely important for the demo because it visually communicates that this isn't just a generic chatbot.

--------------------------------------------------
11. AI TOOL EXECUTION VISUALIZATION
--------------------------------------------------

Since this application is specifically demonstrating an AI customer-support agent, add subtle tool execution states inside the conversation.

For example:

AI is checking billing records...

✓ Retrieved payment history
✓ Detected duplicate transaction
✓ Checked subscription status

Then:

Analysis complete

Do NOT expose raw technical implementation details, API keys, stack traces, or internal prompts.

Make this look like a trustworthy agent activity timeline.

--------------------------------------------------
12. SUPPORT TICKETS
--------------------------------------------------

The existing "Your tickets" panel should be redesigned.

Use ticket cards with:

Ticket title
Category
Status
Created date

Example:

Duplicate payment after upgrade
Billing · Open
Sep 25, 2026

API access on Pro plan
Account · Open
Sep 25, 2026

Use meaningful status colors.

Clicking a ticket should open the conversation/details.

--------------------------------------------------
13. LOGIN PAGE
--------------------------------------------------

Redesign the login page to look like a real SaaS authentication page.

Keep it minimal.

Centered CloudDesk logo.

Card:

Welcome back
Sign in to your CloudDesk account

Email
Password

[Sign in]

Add:
Forgot password?

The demo customer section can remain, but make it visually secondary.

Instead of displaying the demo password prominently, present demo accounts as selectable cards/buttons if the existing application allows it.

Example:

Try a demo account

Healthy free account
Healthy paid account
Duplicate payment
Locked account

Make these look intentional rather than like developer debug information.

--------------------------------------------------
14. TYPOGRAPHY
--------------------------------------------------

Improve typography globally.

Use a modern sans-serif font such as:
Inter
or another clean system/UI font.

Use clear hierarchy:

Page title: 28–32px
Section title: 18–20px
Body: 14–16px
Metadata: 12–13px

Avoid excessive serif typography.

The current application uses a serif-heavy style. Move toward a modern SaaS sans-serif interface.

--------------------------------------------------
15. COMPONENT CONSISTENCY
--------------------------------------------------

Create reusable UI components for:

- Button
- Badge
- StatusBadge
- Card
- MetricCard
- Alert
- Table
- Avatar
- Modal
- Dropdown
- TicketCard
- ChatMessage
- ToolExecution
- ProgressBar

Use consistent:
- Border radius
- Padding
- Font sizes
- Colors
- Shadows
- Hover states
- Focus states

Do not duplicate styles unnecessarily.

--------------------------------------------------
16. RESPONSIVE DESIGN
--------------------------------------------------

Desktop:
Sidebar + main content + optional right context panel.

Tablet:
Collapse sidebar where appropriate.

Mobile:
- Sidebar becomes a drawer
- Cards become single-column
- AI Support context panel moves below/behind a button
- Tables become horizontally scrollable or responsive cards
- Chat input remains accessible at the bottom

--------------------------------------------------
17. MICROINTERACTIONS
--------------------------------------------------

Add subtle, professional interactions:

- Button hover
- Card hover where appropriate
- Sidebar active transitions
- Chat message appearance
- Loading skeletons
- Tool execution progress
- Toast notifications
- Copy-to-clipboard confirmation

Keep animations fast and subtle.

Do not add excessive animations.

--------------------------------------------------
18. ACCESSIBILITY
--------------------------------------------------

Make the UI accessible.

Include:
- Proper semantic HTML
- Keyboard navigation
- Visible focus states
- Accessible buttons
- ARIA labels where needed
- Good color contrast
- Do not rely only on color to communicate status

--------------------------------------------------
19. IMPORTANT DEMO REQUIREMENT
--------------------------------------------------

This application is being used as a portfolio/interview demonstration of an AI customer-support agent.

Therefore, the frontend should subtly communicate the following capabilities:

1. The AI understands the customer's account.
2. The AI can access billing information.
3. The AI can inspect API usage.
4. The AI can reason about customer issues.
5. The AI can use tools.
6. The AI can retrieve relevant account information.
7. The AI can create/route support tickets.
8. The AI can provide grounded answers rather than generic chatbot responses.

Do this through UI design and contextual information, NOT through giant marketing sections.

The application should feel like:

"An actual SaaS customer portal with an AI support agent built into it."

NOT:

"An AI demo website."

--------------------------------------------------
20. FINAL POLISH
--------------------------------------------------

After implementing the redesign:

- Check every page individually.
- Ensure spacing is consistent.
- Ensure no text is clipped.
- Ensure cards align correctly.
- Ensure tables work properly.
- Ensure the AI chat input is always accessible.
- Ensure loading/error/empty states look polished.
- Ensure the application works at 1440px desktop width.
- Ensure mobile layout works.
- Preserve all existing functionality.

Most importantly:

Do not simply change colors.

Perform a complete frontend design refinement while keeping the current product structure and functionality.

The final result should look like a SaaS product that could realistically be shown to a customer or interviewer.