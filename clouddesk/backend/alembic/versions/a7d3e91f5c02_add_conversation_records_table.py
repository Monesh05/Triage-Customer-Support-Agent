# a7d3e91f5c02_add_conversation_records_table.py
# Purpose: Production-hardening follow-up migration (closes the Phase 5/Phase 9 "in-memory
#          conversation registry does not survive a restart" gap documented in README's
#          "Production Deployment" section) — creates the `conversation_records` table
#          (app.models.conversation.ConversationRecord) that app.services.conversation_service
#          now persists a customer conversation's status/final_response/ticket_id to, instead of
#          a module-level `dict`. Note: this migration does NOT create the LangGraph Postgres
#          checkpointer's own tables (`checkpoints`, `checkpoint_writes`, `checkpoint_blobs`,
#          `checkpoint_migrations`) — those are created/versioned by
#          `AsyncPostgresSaver.setup()`, called once at FastAPI startup
#          (app.graph.graph.get_checkpointer, wired in app.main's lifespan). That library owns
#          its own internal migration/versioning table and explicitly documents `.setup()` as the
#          way callers are meant to create/upgrade its schema; hand-copying its raw SQL into an
#          Alembic revision would fight with that internal version tracking the next time the
#          library adds a migration of its own.
# Author: CloudDesk Team
# Date: 2026-09-25

"""add conversation_records table

Revision ID: a7d3e91f5c02
Revises: f3a9c1d8b2e7
Create Date: 2026-09-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a7d3e91f5c02'
down_revision: Union[str, None] = 'f3a9c1d8b2e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'conversation_records',
        sa.Column('thread_id', sa.String(length=64), nullable=False),
        sa.Column('customer_id', sa.String(length=64), nullable=False),
        sa.Column('ticket_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('final_response', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('thread_id'),
    )
    op.create_index(op.f('ix_conversation_records_thread_id'), 'conversation_records', ['thread_id'], unique=True)
    op.create_index(op.f('ix_conversation_records_customer_id'), 'conversation_records', ['customer_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_conversation_records_customer_id'), table_name='conversation_records')
    op.drop_index(op.f('ix_conversation_records_thread_id'), table_name='conversation_records')
    op.drop_table('conversation_records')
