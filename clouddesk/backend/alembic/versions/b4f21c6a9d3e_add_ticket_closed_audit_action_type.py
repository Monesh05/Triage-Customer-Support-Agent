# b4f21c6a9d3e_add_ticket_closed_audit_action_type.py
# Purpose: Post-launch (2026-09-25) migration adding the `ticket_closed` `audit_action_type` enum
#          value, needed by the new customer-facing POST /tickets/{id}/close endpoint
#          (app.services.ticket_service.close_ticket) to audit a customer closing their own
#          ticket, same as every other sensitive ticket/account mutation in this codebase.
# Author: CloudDesk Team
# Date: 2026-09-25

"""add ticket_closed audit_action_type

Revision ID: b4f21c6a9d3e
Revises: a7d3e91f5c02
Create Date: 2026-09-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b4f21c6a9d3e'
down_revision: Union[str, None] = 'a7d3e91f5c02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NEW_AUDIT_ACTION_TYPE: str = "ticket_closed"


def upgrade() -> None:
    op.execute(f"ALTER TYPE audit_action_type ADD VALUE IF NOT EXISTS '{NEW_AUDIT_ACTION_TYPE}'")


def downgrade() -> None:
    # Postgres does not support removing an enum value; the value added in upgrade() is
    # intentionally left in place on downgrade (same convention as f3a9c1d8b2e7's downgrade()).
    pass
