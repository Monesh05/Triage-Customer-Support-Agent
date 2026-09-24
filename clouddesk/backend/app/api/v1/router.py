# app/api/v1/router.py
# Purpose: Aggregates all v1 API routers into a single APIRouter mounted by main.py. Extended in
#          Phase 9 with the customer-facing conversations router (spec section 25).
# Author: CloudDesk Team
# Date: 2026-09-24

from fastapi import APIRouter

from app.api.v1 import (
    accounts,
    api_keys,
    approvals,
    auth,
    conversations,
    entitlements,
    incidents,
    invoices,
    payments,
    refunds,
    subscriptions,
    tickets,
    traces,
    usage,
)
from app.api.v1 import customers as customers_module

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(customers_module.router)
api_router.include_router(accounts.router)
api_router.include_router(subscriptions.router)
api_router.include_router(payments.router)
api_router.include_router(invoices.router)
api_router.include_router(usage.router)
api_router.include_router(api_keys.router)
api_router.include_router(incidents.router)
api_router.include_router(tickets.router)
api_router.include_router(refunds.router)
api_router.include_router(entitlements.router)
api_router.include_router(approvals.router)
api_router.include_router(traces.router)
api_router.include_router(conversations.router)
