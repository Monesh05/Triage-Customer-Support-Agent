# tests/test_api_approvals.py
# Purpose: Integration tests for the approval API (spec sections 7, 22, 26): list, detail,
#          approve, and reject, including 404/409 error cases and an assertion that an
#          approve/reject decision is actually written to the audit log.
# Author: CloudDesk Team
# Date: 2026-09-24

from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.enums import AuditActionType, PaymentStatus
from app.services.approval_service import create_pending_action
from app.services.payment_service import create_refund_request
from tests.conftest import new_id, staff_auth_headers
from tests.factories import create_customer_with_account, create_org_and_plan, create_payment

_PERIOD = datetime(2026, 9, 1, tzinfo=timezone.utc)


async def _make_pending_refund_action(db_session: AsyncSession) -> tuple[object, object]:
    org, _free, pro = await create_org_and_plan(db_session)
    customer = await create_customer_with_account(db_session, org, pro)
    payment = await create_payment(
        db_session, customer, customer.subscriptions[0].id, 49, PaymentStatus.SUCCEEDED, _PERIOD
    )
    await create_refund_request(db_session, payment.id, reason="duplicate charge", actor="billing_agent")
    approval_request = await create_pending_action(
        db_session, customer.id, "thread-api-1", "billing",
        {"agent": "billing", "action": "Refund duplicate payment", "amount": 49.0, "requires_approval": True},
    )
    return customer, approval_request


async def test_list_approvals_returns_pending_only_by_default(client: AsyncClient, db_session: AsyncSession) -> None:
    _customer, approval_request = await _make_pending_refund_action(db_session)

    response = await client.get("/api/v1/approvals", headers=staff_auth_headers())

    assert response.status_code == 200
    body = response.json()
    ids = {item["id"] for item in body}
    assert str(approval_request.id) in ids
    assert all(item["status"] == "pending" for item in body)


async def test_read_approval_detail(client: AsyncClient, db_session: AsyncSession) -> None:
    _customer, approval_request = await _make_pending_refund_action(db_session)

    response = await client.get(f"/api/v1/approvals/{approval_request.id}", headers=staff_auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(approval_request.id)
    assert body["agent_name"] == "billing"
    assert body["amount"] == 49.0


async def test_read_approval_returns_404_for_unknown_id(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/approvals/{new_id()}", headers=staff_auth_headers())

    assert response.status_code == 404


async def test_approve_approval_executes_and_writes_audit_log(client: AsyncClient, db_session: AsyncSession) -> None:
    _customer, approval_request = await _make_pending_refund_action(db_session)

    response = await client.post(
        f"/api/v1/approvals/{approval_request.id}/approve",
        json={"actor": "ops_lead@clouddesk.test"},
        headers=staff_auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["executed"] is True
    assert body["approval_request"]["status"] == "approved"

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action_type == AuditActionType.PENDING_ACTION_APPROVED)
    )
    audit_entries = result.scalars().all()
    assert any(entry.actor == "ops_lead@clouddesk.test" for entry in audit_entries)


async def test_reject_approval_does_not_execute_and_writes_audit_log(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _customer, approval_request = await _make_pending_refund_action(db_session)

    response = await client.post(
        f"/api/v1/approvals/{approval_request.id}/reject",
        json={"actor": "ops_lead@clouddesk.test", "reason": "policy does not allow"},
        headers=staff_auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["executed"] is False
    assert body["approval_request"]["status"] == "rejected"

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action_type == AuditActionType.PENDING_ACTION_REJECTED)
    )
    audit_entries = result.scalars().all()
    assert any(entry.actor == "ops_lead@clouddesk.test" for entry in audit_entries)


async def test_approve_approval_returns_404_for_unknown_id(client: AsyncClient) -> None:
    response = await client.post(
        f"/api/v1/approvals/{new_id()}/approve", json={"actor": "ops_lead"}, headers=staff_auth_headers()
    )

    assert response.status_code == 404


async def test_approve_approval_twice_returns_409(client: AsyncClient, db_session: AsyncSession) -> None:
    _customer, approval_request = await _make_pending_refund_action(db_session)

    first = await client.post(
        f"/api/v1/approvals/{approval_request.id}/approve", json={"actor": "ops_lead"}, headers=staff_auth_headers()
    )
    second = await client.post(
        f"/api/v1/approvals/{approval_request.id}/approve", json={"actor": "ops_lead"}, headers=staff_auth_headers()
    )

    assert first.status_code == 200
    assert second.status_code == 409
