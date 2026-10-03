"""create india_area table for India land and EEZ polygons

Revision ID: 0022_india_area
Revises: 0021_gridded_forecast
Create Date: 2026-10-03 01:50:00.000000+00:00
"""

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0022_india_area"
down_revision: Union[str, None] = "0021_gridded_forecast"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "india_area",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("area_type", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=150), nullable=False),
        sa.Column("area_km2", sa.Float(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                spatial_index=False,
                nullable=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("name", name="uq_india_area_name"),
    )
    op.create_index(
        "idx_india_area_geom",
        "india_area",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index("idx_india_area_geom", table_name="india_area", postgresql_using="gist")
    op.drop_table("india_area")
