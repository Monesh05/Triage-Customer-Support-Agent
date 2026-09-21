# tests/test_tools_technical.py
# Purpose: Tests for app.tools.technical — API usage, API key status (asserts no secret
#          leakage), service status, recent incidents, and the search_error_logs stub. Uses
#          `committed_session` since these tools open their own DB connection.
# Author: CloudDesk Team
# Date: 2026-09-21

from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey
from app.models.enums import IncidentSeverity, IncidentStatus
from app.models.incident import ServiceIncident
from app.models.usage import UsageRecord
from app.tools import technical
from tests.conftest import new_id
from tests.factories import create_customer_with_account, create_org_and_plan

_PERIOD_START = datetime(2026, 9, 1, tzinfo=timezone.utc)
_PERIOD_END = datetime(2026, 9, 30, tzinfo=timezone.utc)
_RAW_SECRET = "sk_live_should_never_appear_in_tool_output"
_KEY_HASH = f"sha256:{_RAW_SECRET}"


async def _register(committed_session: AsyncSession, org) -> None:
    committed_session.info["created_org_ids"].append(org.id)


async def test_get_api_usage_happy_path(committed_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    committed_session.add(
        UsageRecord(
            customer_id=customer.id, api_calls=1000,
            period_start=_PERIOD_START, period_end=_PERIOD_END,
        )
    )
    await committed_session.commit()
    await _register(committed_session, org)

    result = await technical.get_api_usage(customer.id)

    assert result.success is True
    assert result.data[0].api_calls == 1000


async def test_get_api_usage_not_found(committed_session: AsyncSession) -> None:
    result = await technical.get_api_usage(new_id())

    assert result.success is False


async def test_get_api_key_status_never_leaks_secret(committed_session: AsyncSession) -> None:
    org, _free, pro = await create_org_and_plan(committed_session)
    customer = await create_customer_with_account(committed_session, org, pro)
    committed_session.add(ApiKey(customer=customer, key_hash=_KEY_HASH, rate_limit=1000))
    await committed_session.commit()
    await _register(committed_session, org)

    result = await technical.get_api_key_status(customer.id)

    assert result.success is True
    assert len(result.data) == 1
    key_fields = result.data[0].model_dump()
    assert "key_hash" not in key_fields
    assert _RAW_SECRET not in repr(result.data[0])
    assert _RAW_SECRET not in str(key_fields)


async def test_get_service_status_reports_active_incident(committed_session: AsyncSession) -> None:
    committed_session.add(
        ServiceIncident(
            service_name="API-Test",
            status=IncidentStatus.INVESTIGATING,
            severity=IncidentSeverity.HIGH,
            started_at=_PERIOD_START,
            description="Elevated 5xx rates.",
        )
    )
    await committed_session.commit()

    result = await technical.get_service_status("API-Test")

    assert result.success is True
    assert result.data.is_operational is False
    assert result.data.active_incident_id is not None

    await committed_session.execute(
        delete(ServiceIncident).where(ServiceIncident.service_name == "API-Test")
    )
    await committed_session.commit()


async def test_get_service_status_operational_when_no_incidents(committed_session: AsyncSession) -> None:
    result = await technical.get_service_status("NoSuchService-Test")

    assert result.success is True
    assert result.data.is_operational is True
    assert result.data.active_incident_id is None


async def test_get_recent_incidents_returns_list(committed_session: AsyncSession) -> None:
    result = await technical.get_recent_incidents()

    assert result.success is True
    assert isinstance(result.data, list)


async def test_search_error_logs_is_flagged_not_implemented() -> None:
    result = await technical.search_error_logs("403 error")

    assert result.success is False
    assert result.data.not_implemented is True
    assert result.data.entries == []
