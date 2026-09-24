# evaluation/datasets/templates.py
# Purpose: Builds the actual `DatasetRecord` list for each of the 10 required categories (spec
#          section 28), given a map of real seeded customer_ids per scenario. Ticket TEXT is
#          generated programmatically with per-organization phrasing variety (spec Phase 8
#          brief: "generate ticket text programmatically ... as long as it's genuinely varied"),
#          not hand-written one at a time, but each category's two phrasing variants are written
#          out distinctly rather than produced by a single find-and-replace template.
# Author: CloudDesk Team
# Date: 2026-09-24

from evaluation.datasets.schema import (
    CATEGORY_ACCOUNT,
    CATEGORY_ADVERSARIAL,
    CATEGORY_AMBIGUOUS,
    CATEGORY_BILLING,
    CATEGORY_ESCALATION,
    CATEGORY_FALSE_POSITIVE,
    CATEGORY_MULTI_INTENT,
    CATEGORY_POLICY_SENSITIVE,
    CATEGORY_PRODUCT,
    CATEGORY_TECHNICAL,
    DatasetRecord,
)

ORG_SLUGS: tuple[str, ...] = ("acme", "globex", "initech", "umbrella", "stark")

# Scenario keys match the local-part suffixes seeded by clouddesk/data/seed/seed.py's
# `_seed_customers_for_org` (e.g. "{slug}.dupe@customer.example").
CustomerMap = dict[str, dict[str, str]]


def build_billing_tickets(customers: CustomerMap) -> list[DatasetRecord]:
    """Duplicate-charge and failed/pending-payment tickets (spec section 10, Scenario B)."""
    records: list[DatasetRecord] = []
    dupe_variants = [
        "I just checked my card statement and I was charged twice for my subscription this "
        "month. Can you refund the extra charge?",
        "Why does my bank show two separate charges for the same plan this billing period? "
        "This looks like a billing error and I'd like it corrected.",
    ]
    for slug in ORG_SLUGS:
        customer_id = customers["dupe"][slug]
        for i, message in enumerate(dupe_variants):
            records.append(
                DatasetRecord(
                    ticket_id=f"billing-dupe-{slug}-{i}",
                    category=CATEGORY_BILLING,
                    customer_id=customer_id,
                    customer_message=message,
                    expected_intents=["billing"],
                    expected_required_agents=["billing"],
                    expected_priority="high",
                    expected_escalation=False,
                    expected_resolution_keywords=["refund"],
                    notes="Real duplicate-payment customer; a refund should be recommended.",
                )
            )
    return records


def build_billing_payment_status_tickets(customers: CustomerMap) -> list[DatasetRecord]:
    """Failed/pending payment follow-ups, rounding out the billing category."""
    records: list[DatasetRecord] = []
    for slug in ORG_SLUGS[:3]:
        records.append(
            DatasetRecord(
                ticket_id=f"billing-failed-{slug}",
                category=CATEGORY_BILLING,
                customer_id=customers["failed"][slug],
                customer_message="My last payment failed and now my invoice shows overdue. "
                "What happened and what do I need to do?",
                expected_intents=["billing"],
                expected_required_agents=["billing"],
                expected_priority="medium",
                expected_escalation=False,
                expected_resolution_keywords=["payment", "invoice", "failed"],
            )
        )
    for slug in ORG_SLUGS[3:]:
        records.append(
            DatasetRecord(
                ticket_id=f"billing-pending-{slug}",
                category=CATEGORY_BILLING,
                customer_id=customers["pending"][slug],
                customer_message="I paid via bank transfer a few days ago but my invoice still "
                "shows as open/pending. Is this normal?",
                expected_intents=["billing"],
                expected_required_agents=["billing"],
                expected_priority="low",
                expected_escalation=False,
                expected_resolution_keywords=["pending", "payment", "invoice"],
            )
        )
    return records


def build_account_tickets(customers: CustomerMap) -> list[DatasetRecord]:
    """Locked-account tickets (spec section 11, Scenario C)."""
    records: list[DatasetRecord] = []
    variants = [
        "I can't log into my account anymore, it keeps telling me I'm locked out.",
        "My login has been rejected several times today and now I seem to be completely "
        "locked out of the platform. Can you unlock it?",
    ]
    for slug in ORG_SLUGS:
        customer_id = customers["locked"][slug]
        for i, message in enumerate(variants):
            records.append(
                DatasetRecord(
                    ticket_id=f"account-locked-{slug}-{i}",
                    category=CATEGORY_ACCOUNT,
                    customer_id=customer_id,
                    customer_message=message,
                    expected_intents=["account"],
                    expected_required_agents=["account"],
                    expected_priority="high",
                    expected_escalation=False,
                    expected_resolution_keywords=["unlock", "locked"],
                    notes="Real locked-account customer with 7 failed login attempts.",
                )
            )
    return records


def build_technical_tickets(customers: CustomerMap) -> list[DatasetRecord]:
    """Stale-entitlement API-403 tickets (spec section 12, Scenario D)."""
    records: list[DatasetRecord] = []
    variants = [
        "I upgraded my plan yesterday but my API calls are still returning 403 Forbidden.",
        "My API access stopped working after my subscription upgrade went through. It just "
        "returns access denied errors now.",
    ]
    for slug in ORG_SLUGS:
        customer_id = customers["stale"][slug]
        for i, message in enumerate(variants):
            records.append(
                DatasetRecord(
                    ticket_id=f"technical-stale-{slug}-{i}",
                    category=CATEGORY_TECHNICAL,
                    customer_id=customer_id,
                    customer_message=message,
                    expected_intents=["technical", "account"],
                    expected_required_agents=["technical", "account"],
                    expected_priority="high",
                    expected_escalation=False,
                    expected_resolution_keywords=["entitlement", "refresh", "sync"],
                    notes="Real stale-entitlement customer: subscription Pro, entitlement Free.",
                )
            )
    return records


def build_product_tickets(customers: CustomerMap) -> list[DatasetRecord]:
    """Product/FAQ questions answered via RAG (spec section 13, Scenario A)."""
    questions = [
        "Does the Pro plan include full API access?",
        "How does multi-factor authentication work on this platform?",
        "How do I rotate my API key?",
        "What happens to my data if I downgrade my plan?",
        "Is there a rate limit on the Business plan?",
        "How do I add teammates to my organization?",
        "Can I export my usage reports?",
        "What's the difference between Business and Enterprise?",
        "Does upgrading my plan take effect immediately?",
        "How do I view my API usage history?",
    ]
    records: list[DatasetRecord] = []
    for i, question in enumerate(questions):
        slug = ORG_SLUGS[i % len(ORG_SLUGS)]
        scenario = "normal_free" if i % 2 == 0 else "normal_biz"
        records.append(
            DatasetRecord(
                ticket_id=f"product-faq-{i}",
                category=CATEGORY_PRODUCT,
                customer_id=customers[scenario][slug],
                customer_message=question,
                expected_intents=["product"],
                expected_required_agents=["product"],
                expected_priority="low",
                expected_escalation=False,
            )
        )
    return records
