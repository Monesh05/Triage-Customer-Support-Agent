# evaluation/datasets/generate.py
# Purpose: One-time (re-runnable) dataset generation script for Phase 8 (spec section 28).
#          Queries the REAL dev `clouddesk` database for the 40 customers Phase 1's seed script
#          created (clouddesk/data/seed/seed.py) to build a scenario_key -> {org_slug:
#          customer_id} map, then hands that map to evaluation/datasets/templates*.py to build
#          >=100 DatasetRecord tickets and writes them to evaluation/datasets/tickets.jsonl.
#
#          Run with (from the repo root, backend venv active):
#              python -m evaluation.datasets.generate
#
#          The generated file bakes in real customer UUIDs from whatever database it was run
#          against; re-run this after re-seeding a fresh database if customer ids change.
# Author: CloudDesk Team
# Date: 2026-09-24

import asyncio
import json
import logging

import evaluation  # noqa: F401  (activates the sys.path shim before any `app.*` import below)
from sqlalchemy import select

from app.database.engine import AsyncSessionFactory
from app.models.customer import Customer
from evaluation.datasets.schema import DatasetRecord
from evaluation.datasets.templates import (
    ORG_SLUGS,
    CustomerMap,
    build_account_tickets,
    build_billing_payment_status_tickets,
    build_billing_tickets,
    build_product_tickets,
    build_technical_tickets,
)
from evaluation.datasets.templates_advanced import (
    build_adversarial_tickets,
    build_ambiguous_tickets,
    build_escalation_tickets,
    build_false_positive_tickets,
    build_multi_intent_tickets,
    build_policy_sensitive_tickets,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("evaluation.datasets.generate")

OUTPUT_PATH = "evaluation/datasets/tickets.jsonl"

# Scenario key -> the email local-part suffix seed.py used for it (see data/seed/seed.py's
# `_seed_customers_for_org`).
SCENARIO_EMAIL_SUFFIX: dict[str, str] = {
    "dupe": "dupe",
    "failed": "failed",
    "pending": "pending",
    "stale": "stale",
    "locked": "locked",
    "heavyuser": "heavyuser",
    "normal_free": "normal.free",
    "normal_biz": "normal.biz",
}


async def _fetch_customer_map() -> CustomerMap:
    """Query every seeded customer and index them by (scenario_key -> org_slug -> customer_id)."""
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(Customer.id, Customer.email))
        rows = result.all()

    by_email = {email: str(customer_id) for customer_id, email in rows}
    customer_map: CustomerMap = {key: {} for key in SCENARIO_EMAIL_SUFFIX}
    for slug in ORG_SLUGS:
        for scenario_key, suffix in SCENARIO_EMAIL_SUFFIX.items():
            email = f"{slug}.{suffix}@customer.example"
            if email not in by_email:
                raise RuntimeError(
                    f"Expected seeded customer '{email}' not found — run "
                    "`python -m data.seed.seed` against this database first."
                )
            customer_map[scenario_key][slug] = by_email[email]
    return customer_map


def _build_all_records(customers: CustomerMap) -> list[DatasetRecord]:
    builders = (
        build_billing_tickets,
        build_billing_payment_status_tickets,
        build_account_tickets,
        build_technical_tickets,
        build_product_tickets,
        build_multi_intent_tickets,
        build_ambiguous_tickets,
        build_escalation_tickets,
        build_false_positive_tickets,
        build_policy_sensitive_tickets,
        build_adversarial_tickets,
    )
    records: list[DatasetRecord] = []
    for builder in builders:
        records.extend(builder(customers))
    return records


async def run_generate() -> None:
    logger.info("Fetching seeded customer ids from the database...")
    customers = await _fetch_customer_map()
    records = _build_all_records(customers)
    logger.info("Generated %d dataset records across %d builders.", len(records), 11)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for record in records:
            f.write(record.model_dump_json() + "\n")
    logger.info("Wrote dataset to %s", OUTPUT_PATH)


if __name__ == "__main__":
    asyncio.run(run_generate())
