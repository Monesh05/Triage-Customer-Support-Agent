# app/tools/billing.py
# Purpose: Billing Agent tool layer (spec section 10): subscriptions, payment history,
#          invoices, refund calculation/creation, and billing policy lookup. Each function
#          opens its own session via app.database.session.get_session() and delegates all
#          logic to app.services.* — no raw SQL, no direct DB access.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid
from decimal import Decimal

from app.database.session import get_session
from app.models.enums import PaymentStatus
from app.schemas.invoice import InvoiceResponse
from app.schemas.payment import PaymentResponse
from app.schemas.subscription import SubscriptionResponse
from app.services import payment_service, policy_service, subscription_service
from app.services.exceptions import InvalidStateError, NotFoundError
from app.services.invoice_service import get_invoices_by_customer
from app.tools.base import ToolInputError, ToolResult, log_tool_call, parse_uuid
from app.tools.schemas import BillingPolicyData, RefundCalculationData, RefundRequestData

DEFAULT_REFUND_ACTOR: str = "billing_agent"


async def get_subscription(customer_id: str | uuid.UUID) -> ToolResult[list[SubscriptionResponse]]:
    """Fetch all subscriptions (with plan + entitlement) for a customer."""
    try:
        cid = parse_uuid(customer_id, "customer_id")
        async with get_session() as session:
            subs = await subscription_service.get_subscriptions_by_customer(session, cid)
            data = [SubscriptionResponse.model_validate(s) for s in subs]
        return ToolResult(success=True, data=data)
    except (ToolInputError, NotFoundError) as exc:
        return ToolResult(success=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001 - never let unexpected errors escape the tool layer
        return ToolResult(success=False, error=f"Unexpected error in get_subscription: {exc}")


async def get_payment_history(customer_id: str | uuid.UUID) -> ToolResult[list[PaymentResponse]]:
    """Fetch a customer's payment history, most recent first."""
    try:
        cid = parse_uuid(customer_id, "customer_id")
        async with get_session() as session:
            payments = await payment_service.get_payments_by_customer(session, cid)
            data = [PaymentResponse.model_validate(p) for p in payments]
        return ToolResult(success=True, data=data)
    except (ToolInputError, NotFoundError) as exc:
        return ToolResult(success=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ToolResult(success=False, error=f"Unexpected error in get_payment_history: {exc}")


async def get_invoice(customer_id: str | uuid.UUID) -> ToolResult[list[InvoiceResponse]]:
    """Fetch all invoices issued to a customer, most recent first."""
    try:
        cid = parse_uuid(customer_id, "customer_id")
        async with get_session() as session:
            invoices = await get_invoices_by_customer(session, cid)
            data = [InvoiceResponse.model_validate(inv) for inv in invoices]
        return ToolResult(success=True, data=data)
    except (ToolInputError, NotFoundError) as exc:
        return ToolResult(success=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ToolResult(success=False, error=f"Unexpected error in get_invoice: {exc}")


async def calculate_refund(payment_id: str | uuid.UUID) -> ToolResult[RefundCalculationData]:
    """Compute the refundable amount for a payment WITHOUT creating a refund request."""
    try:
        pid = parse_uuid(payment_id, "payment_id")
        async with get_session() as session:
            payment = await payment_service.get_payment_by_id(session, pid)
            is_eligible = payment.status == PaymentStatus.SUCCEEDED
            amount: Decimal = (
                payment_service.calculate_refund_amount(payment) if is_eligible else Decimal("0")
            )
            reason = (
                "Payment succeeded; full amount is refundable."
                if is_eligible
                else f"Payment status is {payment.status.value}; not refundable."
            )
            data = RefundCalculationData(
                payment_id=payment.id,
                is_eligible=is_eligible,
                refundable_amount=float(amount),
                currency=payment.currency,
                reason=reason,
            )
        return ToolResult(success=True, data=data)
    except (ToolInputError, NotFoundError) as exc:
        return ToolResult(success=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ToolResult(success=False, error=f"Unexpected error in calculate_refund: {exc}")


async def get_billing_policy(policy_key: str) -> ToolResult[BillingPolicyData]:
    """Look up a support policy (e.g. 'refund_rules', 'cancellation_rules') by its key."""
    try:
        async with get_session() as session:
            policy = await policy_service.get_policy_by_key(session, policy_key)
            data = BillingPolicyData(
                policy_key=policy.policy_key,
                title=policy.title,
                description=policy.description,
                rules=policy.rules,
            )
        return ToolResult(success=True, data=data)
    except NotFoundError as exc:
        return ToolResult(success=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ToolResult(success=False, error=f"Unexpected error in get_billing_policy: {exc}")


async def create_refund_request(
    payment_id: str | uuid.UUID, reason: str, actor: str = DEFAULT_REFUND_ACTOR
) -> ToolResult[RefundRequestData]:
    """Create a PENDING_APPROVAL refund request for a payment (sensitive/mutating action).

    Never claims the refund was processed — only that a request was created (spec section 27).
    """
    try:
        pid = parse_uuid(payment_id, "payment_id")
        async with get_session() as session:
            refund = await payment_service.create_refund_request(session, pid, reason, actor)
            log_tool_call("create_refund_request", refund.customer_id, f"created refund {refund.id}")
            data = RefundRequestData(
                id=refund.id,
                payment_id=refund.payment_id,
                customer_id=refund.customer_id,
                amount=float(refund.amount),
                reason=refund.reason,
                status=refund.status.value,
                created_at=refund.created_at,
            )
        return ToolResult(success=True, data=data)
    except (ToolInputError, NotFoundError, InvalidStateError) as exc:
        return ToolResult(success=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ToolResult(success=False, error=f"Unexpected error in create_refund_request: {exc}")
