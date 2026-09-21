# app/api/v1/api_keys.py
# Purpose: REST endpoint for retrieving a customer's API key metadata (spec section 7).
#          Response schema never includes key_hash or raw secret material.
# Author: CloudDesk Team
# Date: 2026-09-21

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.schemas.api_key import ApiKeyResponse
from app.services.api_key_service import get_api_keys_by_customer

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("/{customer_id}", response_model=list[ApiKeyResponse])
async def read_api_keys(
    customer_id: uuid.UUID, session: AsyncSession = Depends(get_db_session)
) -> list[ApiKeyResponse]:
    """Return API key metadata (never raw keys/hashes) for a customer."""
    api_keys = await get_api_keys_by_customer(session, customer_id)
    return [ApiKeyResponse.model_validate(k) for k in api_keys]
