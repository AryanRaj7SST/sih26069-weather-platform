"""Evidence and Corroboration Schema Foundation

Revision ID: 0002_evidence_schema
Revises: 0001_initial_schema
Create Date: 2026-08-29 14:15:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_evidence_schema"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update weather_observations with water_level_m, external_id, and indexes
    op.add_column(
        "weather_observations",
        sa.Column("external_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "weather_observations",
        sa.Column("water_level_m", sa.Float(), nullable=True),
    )
    op.create_index(
        op.f("ix_weather_observations_external_id"),
        "weather_observations",
        ["external_id"],
        unique=False,
    )
    op.create_index(
        "idx_weather_observations_source_external",
        "weather_observations",
        ["source_id", "external_id"],
        unique=False,
    )
    op.create_index(
        "idx_weather_observations_station_time",
        "weather_observations",
        ["station_code", sa.text("observed_at DESC")],
        unique=False,
    )

    # 2. Create evidence_items table
    op.create_table(
        "evidence_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sources.id"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column(
            "evidence_type",
            sa.String(length=50),
            nullable=False,
            server_default="NEWS_ARTICLE",
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("publisher_domain", sa.String(length=150), nullable=True),
        sa.Column(
            "language",
            sa.String(length=50),
            nullable=True,
            server_default="English",
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("text_snippet", sa.Text(), nullable=True),
        sa.Column("sha256_hash", sa.String(length=64), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evidence_items_external_id"),
        "evidence_items",
        ["external_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evidence_items_published_at"),
        "evidence_items",
        ["published_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evidence_items_publisher_domain"),
        "evidence_items",
        ["publisher_domain"],
        unique=False,
    )
    op.create_index(
        "idx_evidence_items_source_external",
        "evidence_items",
        ["source_id", "external_id"],
        unique=True,
    )
    op.create_index(
        "idx_evidence_items_published_at",
        "evidence_items",
        [sa.text("published_at DESC")],
        unique=False,
    )
    op.create_index(
        "idx_evidence_items_domain",
        "evidence_items",
        ["publisher_domain"],
        unique=False,
    )

    # 3. Create incident_evidence_links table
    op.create_table(
        "incident_evidence_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("weather_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evidence_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "link_role",
            sa.String(length=50),
            nullable=False,
            server_default="SUPPORTING_EVIDENCE",
        ),
        sa.Column(
            "confidence_score",
            sa.Float(),
            nullable=False,
            server_default="0.5",
        ),
        sa.Column(
            "match_explanation",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", "evidence_id", name="uq_incident_evidence_link"),
    )
    op.create_index(
        "idx_incident_evidence_report_id",
        "incident_evidence_links",
        ["report_id"],
        unique=False,
    )
    op.create_index(
        "idx_incident_evidence_evidence_id",
        "incident_evidence_links",
        ["evidence_id"],
        unique=False,
    )

    # 4. Create incident_observation_corroborations table
    op.create_table(
        "incident_observation_corroborations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("weather_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "observation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("weather_observations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("distance_meters", sa.Float(), nullable=False),
        sa.Column("time_delta_seconds", sa.Integer(), nullable=False),
        sa.Column("corroboration_score", sa.Float(), nullable=False),
        sa.Column("corroboration_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "report_id",
            "observation_id",
            name="uq_incident_observation_corroboration",
        ),
    )
    op.create_index(
        "idx_corroboration_report_id",
        "incident_observation_corroborations",
        ["report_id"],
        unique=False,
    )
    op.create_index(
        "idx_corroboration_observation_id",
        "incident_observation_corroborations",
        ["observation_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop in reverse order
    op.drop_table("incident_observation_corroborations")
    op.drop_table("incident_evidence_links")
    op.drop_table("evidence_items")
    op.drop_index("idx_weather_observations_station_time", table_name="weather_observations")
    op.drop_index("idx_weather_observations_source_external", table_name="weather_observations")
    op.drop_index(op.f("ix_weather_observations_external_id"), table_name="weather_observations")
    op.drop_column("weather_observations", "water_level_m")
    op.drop_column("weather_observations", "external_id")
