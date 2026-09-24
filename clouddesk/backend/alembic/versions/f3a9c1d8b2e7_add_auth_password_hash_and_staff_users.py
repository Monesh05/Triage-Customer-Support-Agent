# f3a9c1d8b2e7_add_auth_password_hash_and_staff_users.py
# Purpose: Phase 10 migration (spec section 27) — adds `customers.password_hash` for customer
#          login, creates the `staff_users` table for internal support-console accounts, and adds
#          two new `audit_action_type` enum values (login_succeeded, login_failed) so login
#          attempts can be audited like every other sensitive action.
# Author: CloudDesk Team
# Date: 2026-09-24

"""add auth password_hash and staff_users

Revision ID: f3a9c1d8b2e7
Revises: dcf0da22e2a6
Create Date: 2026-09-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f3a9c1d8b2e7'
down_revision: Union[str, None] = 'dcf0da22e2a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NEW_AUDIT_ACTION_TYPES: tuple[str, ...] = ("login_succeeded", "login_failed")


def upgrade() -> None:
    for value in NEW_AUDIT_ACTION_TYPES:
        op.execute(f"ALTER TYPE audit_action_type ADD VALUE IF NOT EXISTS '{value}'")

    op.add_column("customers", sa.Column("password_hash", sa.String(length=255), nullable=True))

    op.create_table(
        "staff_users",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )


def downgrade() -> None:
    op.drop_table("staff_users")
    op.drop_column("customers", "password_hash")
    # Note: Postgres does not support removing enum values; the two audit_action_type values
    # added in upgrade() are intentionally left in place on downgrade.
