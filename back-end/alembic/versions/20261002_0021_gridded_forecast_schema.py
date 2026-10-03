"""create weather_grid_forecast and marine_grid_forecast tables

Revision ID: 0021_gridded_forecast
Revises: 0020_image_forensics
Create Date: 2026-10-02 03:00:00.000000+00:00
"""

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0021_gridded_forecast"
down_revision: Union[str, None] = "0020_image_forensics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. weather_grid_forecast table
    op.create_table(
        "weather_grid_forecast",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("valid_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("temperature_2m", sa.Float(), nullable=True),
        sa.Column("precipitation", sa.Float(), nullable=True),
        sa.Column("wind_speed_10m", sa.Float(), nullable=True),
        sa.Column("wind_direction_10m", sa.Float(), nullable=True),
        sa.Column("pressure_msl", sa.Float(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                spatial_index=False,
            ),
            nullable=False,
        ),
        sa.Column("source_name", sa.String(length=100), nullable=False, server_default="OPEN_METEO"),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "latitude", "longitude", "valid_time",
            name="uq_weather_grid_forecast_lat_lon_time",
        ),
    )

    op.create_index(
        "idx_weather_grid_forecast_geom",
        "weather_grid_forecast",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        "idx_weather_grid_forecast_valid_time",
        "weather_grid_forecast",
        ["valid_time"],
        unique=False,
    )
    op.create_index(
        "idx_weather_grid_forecast_lat_lon",
        "weather_grid_forecast",
        ["latitude", "longitude"],
        unique=False,
    )

    # 2. marine_grid_forecast table
    op.create_table(
        "marine_grid_forecast",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("valid_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("wave_height", sa.Float(), nullable=True),
        sa.Column("wave_direction", sa.Float(), nullable=True),
        sa.Column("wave_period", sa.Float(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                spatial_index=False,
            ),
            nullable=False,
        ),
        sa.Column("source_name", sa.String(length=100), nullable=False, server_default="OPEN_METEO_MARINE"),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "latitude", "longitude", "valid_time",
            name="uq_marine_grid_forecast_lat_lon_time",
        ),
    )

    op.create_index(
        "idx_marine_grid_forecast_geom",
        "marine_grid_forecast",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        "idx_marine_grid_forecast_valid_time",
        "marine_grid_forecast",
        ["valid_time"],
        unique=False,
    )
    op.create_index(
        "idx_marine_grid_forecast_lat_lon",
        "marine_grid_forecast",
        ["latitude", "longitude"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_marine_grid_forecast_lat_lon", table_name="marine_grid_forecast")
    op.drop_index("idx_marine_grid_forecast_valid_time", table_name="marine_grid_forecast")
    op.drop_index("idx_marine_grid_forecast_geom", table_name="marine_grid_forecast", postgresql_using="gist")
    op.drop_table("marine_grid_forecast")

    op.drop_index("idx_weather_grid_forecast_lat_lon", table_name="weather_grid_forecast")
    op.drop_index("idx_weather_grid_forecast_valid_time", table_name="weather_grid_forecast")
    op.drop_index("idx_weather_grid_forecast_geom", table_name="weather_grid_forecast", postgresql_using="gist")
    op.drop_table("weather_grid_forecast")
