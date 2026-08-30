"""Realtime Outbox Schema for Transactional Event Delivery

Revision ID: 0004_realtime_outbox_schema
Revises: 0003_corroboration_hardening
Create Date: 2026-08-30 17:30:00.000000+00:00

Additive migration creating the realtime_outbox table to guarantee atomic
persistence between PostgreSQL domain transactions and outbound Redis Stream events.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_realtime_outbox_schema"
down_revision: Union[str, None] = "0003_corroboration_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create realtime_outbox table
    op.create_table(
        "realtime_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("tracking_id", sa.String(50), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(20), server_default="PENDING", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="5", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 2. Create indexes
    op.create_index(
        "idx_realtime_outbox_event_id",
        "realtime_outbox",
        ["event_id"],
        unique=True,
    )
    op.create_index(
        "idx_realtime_outbox_event_type",
        "realtime_outbox",
        ["event_type"],
    )
    op.create_index(
        "idx_realtime_outbox_entity_id",
        "realtime_outbox",
        ["entity_id"],
    )
    op.create_index(
        "idx_realtime_outbox_status",
        "realtime_outbox",
        ["status"],
    )
    op.create_index(
        "idx_realtime_outbox_created_at",
        "realtime_outbox",
        ["created_at"],
    )
    op.create_index(
        "idx_realtime_outbox_pending_retry",
        "realtime_outbox",
        ["status", "next_retry_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_realtime_outbox_pending_retry", table_name="realtime_outbox")
    op.drop_index("idx_realtime_outbox_created_at", table_name="realtime_outbox")
    op.drop_index("idx_realtime_outbox_status", table_name="realtime_outbox")
    op.drop_index("idx_realtime_outbox_entity_id", table_name="realtime_outbox")
    op.drop_index("idx_realtime_outbox_event_type", table_name="realtime_outbox")
    op.drop_index("idx_realtime_outbox_event_id", table_name="realtime_outbox")
    op.drop_table("realtime_outbox")
