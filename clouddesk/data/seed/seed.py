# seed.py
# Purpose: Populates the CloudDesk PostgreSQL database with realistic Phase 1 seed data:
#          organizations, plans, support policies, service incidents, and ~40 customers
#          spanning healthy, duplicate-payment, failed/pending-payment, stale-entitlement,
#          locked-account, and false-positive-high-usage scenarios (spec section 6).
#
#          Run with:  python -m data.seed.seed   (from clouddesk/backend, with the
#          backend's virtualenv active and DATABASE_URL pointing at the running Postgres.)
# Author: CloudDesk Team
# Date: 2026-09-21

import asyncio
import logging
import os
import sys

# Ensure the `app` package (clouddesk/backend/app) is importable regardless of CWD.
_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for path in (_BACKEND_DIR, _REPO_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.logging import configure_logging  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.database.engine import AsyncSessionFactory  # noqa: E402
from app.models.enums import IncidentSeverity, IncidentStatus  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models.plan import Plan  # noqa: E402
from app.models.policy import SupportPolicy  # noqa: E402
from app.models.staff_user import StaffUser  # noqa: E402
from data.seed.builders import build_incident, build_organization, build_plan, utc  # noqa: E402
from data.seed.constants import (  # noqa: E402
    ORGANIZATION_SEEDS,
    PLAN_SEEDS,
    SUPPORT_POLICY_SEEDS,
)
from data.seed import scenarios  # noqa: E402

configure_logging()
logger = logging.getLogger(__name__)


async def _seed_plans(session: AsyncSession) -> dict[str, Plan]:
    plans: dict[str, Plan] = {}
    for spec in PLAN_SEEDS:
        plan = build_plan(**spec)
        session.add(plan)
        plans[spec["name"]] = plan
    await session.flush()
    return plans


async def _seed_organizations(session: AsyncSession) -> dict[str, Organization]:
    orgs: dict[str, Organization] = {}
    for spec in ORGANIZATION_SEEDS:
        org = build_organization(spec["name"], spec["domain"])
        session.add(org)
        orgs[spec["name"]] = org
    await session.flush()
    return orgs


async def _seed_policies(session: AsyncSession) -> None:
    for spec in SUPPORT_POLICY_SEEDS:
        session.add(SupportPolicy(**spec))


# Single demo staff/support-console account (Phase 10, spec section 27). A config-driven single
# admin credential (rather than a whole staff-management UI) is the right scope for this project:
# there is no requirement anywhere in the spec for multiple staff roles/permissions, only a
# customer-vs-staff distinction, so one seeded account fully exercises that distinction in tests
# and manual verification without over-building unused staff-management tooling.
STAFF_DEMO_EMAIL: str = "staff@clouddesk.example"
STAFF_DEMO_PASSWORD: str = "staff1234"


async def _seed_staff_user(session: AsyncSession) -> None:
    session.add(
        StaffUser(
            name="Support Console Staff",
            email=STAFF_DEMO_EMAIL,
            password_hash=hash_password(STAFF_DEMO_PASSWORD),
        )
    )


async def _seed_incidents(session: AsyncSession) -> None:
    session.add_all(
        [
            build_incident(
                "API", IncidentStatus.MONITORING, IncidentSeverity.HIGH,
                utc(2026, 9, 20, 14),
                "Elevated 5xx error rates on the public API gateway; mitigation deployed.",
            ),
            build_incident(
                "Authentication", IncidentStatus.INVESTIGATING, IncidentSeverity.MEDIUM,
                utc(2026, 9, 21, 8),
                "Intermittent login failures for a subset of customers; under investigation.",
            ),
            build_incident(
                "Billing", IncidentStatus.IDENTIFIED, IncidentSeverity.LOW,
                utc(2026, 9, 19, 22),
                "Invoice generation delayed by up to 6 hours due to a batch job backlog.",
            ),
            build_incident(
                "API", IncidentStatus.RESOLVED, IncidentSeverity.CRITICAL,
                utc(2026, 8, 10, 3), "Full API outage caused by a bad deploy.",
                resolved_at=utc(2026, 8, 10, 5),
            ),
        ]
    )


async def _seed_customers_for_org(
    session: AsyncSession, org: Organization, plans: dict[str, Plan], slug: str
) -> None:
    """Create the full scenario mix (8 customers) for a single organization."""
    free, pro, business, enterprise = plans["Free"], plans["Pro"], plans["Business"], plans["Enterprise"]

    scenarios.seed_normal_customer(session, org, f"{slug} Normal Free", f"{slug}.normal.free@customer.example", free)
    scenarios.seed_normal_customer(session, org, f"{slug} Normal Business", f"{slug}.normal.biz@customer.example", business)
    scenarios.seed_duplicate_payment_customer(session, org, f"{slug} Duplicate Charge", f"{slug}.dupe@customer.example", pro)
    scenarios.seed_failed_payment_customer(session, org, f"{slug} Failed Payment", f"{slug}.failed@customer.example", pro)
    scenarios.seed_pending_payment_customer(session, org, f"{slug} Pending Payment", f"{slug}.pending@customer.example", pro)
    scenarios.seed_stale_entitlement_customer(
        session, org, f"{slug} Stale Entitlement", f"{slug}.stale@customer.example", pro, free
    )
    scenarios.seed_locked_account_customer(session, org, f"{slug} Locked Out", f"{slug}.locked@customer.example", pro)
    scenarios.seed_false_positive_high_usage_customer(
        session, org, f"{slug} Heavy Legit User", f"{slug}.heavyuser@customer.example", enterprise
    )


async def _already_seeded(session: AsyncSession) -> bool:
    result = await session.execute(select(Organization.id).limit(1))
    return result.scalar_one_or_none() is not None


async def run_seed() -> None:
    async with AsyncSessionFactory() as session:
        if await _already_seeded(session):
            logger.warning("Database already contains organizations; skipping seed to avoid duplicates.")
            return

        try:
            plans = await _seed_plans(session)
            orgs = await _seed_organizations(session)
            await _seed_policies(session)
            await _seed_incidents(session)
            await _seed_staff_user(session)

            for slug, org in zip(
                ["acme", "globex", "initech", "umbrella", "stark"], orgs.values(), strict=True
            ):
                await _seed_customers_for_org(session, org, plans, slug)

            await session.commit()
        except Exception:
            logger.exception("Seeding failed; rolling back all changes.")
            await session.rollback()
            raise

    logger.info("Seed complete: %d organizations, %d plans, 40 customers.", len(ORGANIZATION_SEEDS), len(PLAN_SEEDS))


if __name__ == "__main__":
    asyncio.run(run_seed())
