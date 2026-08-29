"""Initial database schema for SIH26069 Weather Platform

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-29 07:10:00.000000+00:00

"""

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure PostGIS extension is available
    op.execute('CREATE EXTENSION IF NOT EXISTS "postgis";')

    # 1. users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="DEOC_OFFICER"),
        sa.Column("jurisdiction_code", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # 2. sources
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("base_trust_score", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_code"),
    )

    # 3. event_categories
    op.create_table(
        "event_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("category_code", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column(
            "severity_default",
            sa.String(length=20),
            nullable=False,
            server_default="MODERATE",
        ),
        sa.Column("color_hex", sa.String(length=10), nullable=False),
        sa.Column("icon_name", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category_code"),
    )

    # 4. weather_reports
    op.create_table(
        "weather_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tracking_id", sa.String(length=32), nullable=False),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sources.id"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("event_categories.id"),
            nullable=True,
        ),
        sa.Column("reported_category", sa.String(length=100), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="MODERATE"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location_name", sa.String(length=255), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
                spatial_index=False,
            ),
            nullable=False,
        ),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "processing_status",
            sa.String(length=30),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "verification_status",
            sa.String(length=30),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("credibility_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "credibility_explanation",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("text_embedding", sa.ARRAY(sa.Float()), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.UniqueConstraint("tracking_id"),
    )
    op.create_index(
        op.f("ix_weather_reports_tracking_id"), "weather_reports", ["tracking_id"], unique=True
    )
    op.create_index(
        op.f("ix_weather_reports_external_id"), "weather_reports", ["external_id"], unique=False
    )
    op.create_index(
        op.f("ix_weather_reports_occurred_at"), "weather_reports", ["occurred_at"], unique=False
    )
    op.create_index(
        op.f("ix_weather_reports_verification_status"),
        "weather_reports",
        ["verification_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_weather_reports_credibility_score"),
        "weather_reports",
        ["credibility_score"],
        unique=False,
    )
    op.create_index(
        op.f("ix_weather_reports_created_at"), "weather_reports", ["created_at"], unique=False
    )
    op.create_index(
        "idx_weather_reports_geom",
        "weather_reports",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        "idx_weather_reports_status_time",
        "weather_reports",
        ["verification_status", sa.text("occurred_at DESC")],
        unique=False,
    )
    op.create_index(
        "idx_weather_reports_credibility",
        "weather_reports",
        [sa.text("credibility_score DESC")],
        unique=False,
    )
    op.create_index(
        "idx_weather_reports_source_external",
        "weather_reports",
        ["source_id", "external_id"],
        unique=False,
    )

    # 5. report_media
    op.create_table(
        "report_media",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("weather_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("media_type", sa.String(length=30), nullable=False),
        sa.Column("storage_bucket", sa.String(length=100), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("exif_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 6. weather_observations
    op.create_table(
        "weather_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sources.id"),
            nullable=False,
        ),
        sa.Column("station_code", sa.String(length=50), nullable=False),
        sa.Column("station_name", sa.String(length=150), nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
                spatial_index=False,
            ),
            nullable=False,
        ),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("humidity_pct", sa.Float(), nullable=True),
        sa.Column("rainfall_mm", sa.Float(), nullable=True),
        sa.Column("wind_speed_kmh", sa.Float(), nullable=True),
        sa.Column("wind_direction_deg", sa.Integer(), nullable=True),
        sa.Column("pressure_hpa", sa.Float(), nullable=True),
        sa.Column("raw_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_weather_observations_station_code"),
        "weather_observations",
        ["station_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_weather_observations_observed_at"),
        "weather_observations",
        ["observed_at"],
        unique=False,
    )
    op.create_index(
        "idx_weather_observations_geom",
        "weather_observations",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )

    # 7. duplicate_clusters
    op.create_table(
        "duplicate_clusters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "primary_report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("weather_reports.id"),
            nullable=False,
        ),
        sa.Column("cluster_radius_meters", sa.Float(), nullable=False, server_default="2500.0"),
        sa.Column(
            "centroid_geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
                spatial_index=False,
            ),
            nullable=False,
        ),
        sa.Column("member_count", sa.Integer(), nullable=False, server_default="1"),
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
    )
    op.create_index(
        "idx_duplicate_clusters_centroid_geom",
        "duplicate_clusters",
        ["centroid_geom"],
        unique=False,
        postgresql_using="gist",
    )

    # 8. duplicate_members
    op.create_table(
        "duplicate_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cluster_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("duplicate_clusters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("weather_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 9. verification_events
    op.create_table(
        "verification_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("weather_reports.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("previous_status", sa.String(length=30), nullable=False),
        sa.Column("new_status", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "action_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 10. ingestion_runs
    op.create_table(
        "ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sources.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("records_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_ingested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_duplicate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # 11. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("ingestion_runs")
    op.drop_table("verification_events")
    op.drop_table("duplicate_members")
    op.drop_table("duplicate_clusters")
    op.drop_table("weather_observations")
    op.drop_table("report_media")
    op.drop_table("weather_reports")
    op.drop_table("event_categories")
    op.drop_table("sources")
    op.drop_table("users")
