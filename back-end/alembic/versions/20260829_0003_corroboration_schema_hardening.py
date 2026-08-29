"""Corroboration Schema Hardening

Revision ID: 0003_corroboration_hardening
Revises: 0002_evidence_schema
Create Date: 2026-08-29 16:00:00.000000+00:00

Additive migration to support structured observation corroboration assessments:
- Add corroboration_assessment (JSONB) column for structured engine output
- Add updated_at (TIMESTAMPTZ) column for idempotent update tracking
- Make distance_meters nullable (handles missing coordinates)
- Make time_delta_seconds nullable (handles missing timestamps)
- Preserves existing corroboration_notes TEXT column
- Non-destructive: existing rows remain valid
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_corroboration_hardening"
down_revision: Union[str, None] = "0002_evidence_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add structured assessment JSONB column
    op.add_column(
        "incident_observation_corroborations",
        sa.Column(
            "corroboration_assessment",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # 2. Add updated_at column with server default for existing rows
    op.add_column(
        "incident_observation_corroborations",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # 3. Make distance_meters nullable (was NOT NULL)
    op.alter_column(
        "incident_observation_corroborations",
        "distance_meters",
        existing_type=sa.Float(),
        nullable=True,
    )

    # 4. Make time_delta_seconds nullable (was NOT NULL)
    op.alter_column(
        "incident_observation_corroborations",
        "time_delta_seconds",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    # Reverse in opposite order

    # 4. Restore NOT NULL on time_delta_seconds (set existing NULLs to 0 first)
    op.execute(
        "UPDATE incident_observation_corroborations "
        "SET time_delta_seconds = 0 WHERE time_delta_seconds IS NULL"
    )
    op.alter_column(
        "incident_observation_corroborations",
        "time_delta_seconds",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # 3. Restore NOT NULL on distance_meters (set existing NULLs to 0.0 first)
    op.execute(
        "UPDATE incident_observation_corroborations "
        "SET distance_meters = 0.0 WHERE distance_meters IS NULL"
    )
    op.alter_column(
        "incident_observation_corroborations",
        "distance_meters",
        existing_type=sa.Float(),
        nullable=False,
    )

    # 2. Drop updated_at column
    op.drop_column("incident_observation_corroborations", "updated_at")

    # 1. Drop corroboration_assessment column
    op.drop_column("incident_observation_corroborations", "corroboration_assessment")
