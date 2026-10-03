import uuid
from datetime import datetime
from typing import Any, Optional

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IndiaArea(Base):
    __tablename__ = "india_area"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    area_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "LAND", "EEZ"
    source: Mapped[str] = mapped_column(String(150), nullable=False)
    area_km2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    geom: Mapped[Any] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("name", name="uq_india_area_name"),
        Index("idx_india_area_geom", "geom", postgresql_using="gist"),
    )
