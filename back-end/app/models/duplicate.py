import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, List

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.report import WeatherReport


class DuplicateCluster(Base):
    __tablename__ = "duplicate_clusters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    primary_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("weather_reports.id"),
        nullable=False,
    )
    cluster_radius_meters: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=2500.0,
    )
    centroid_geom: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True),
        nullable=False,
    )
    member_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    primary_report: Mapped["WeatherReport"] = relationship(
        "WeatherReport",
        back_populates="primary_cluster",
        foreign_keys=[primary_report_id],
    )
    members: Mapped[List["DuplicateMember"]] = relationship(
        "DuplicateMember",
        back_populates="cluster",
        cascade="all, delete-orphan",
    )


class DuplicateMember(Base):
    __tablename__ = "duplicate_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("duplicate_clusters.id", ondelete="CASCADE"),
        nullable=False,
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("weather_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    similarity_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    cluster: Mapped["DuplicateCluster"] = relationship(
        "DuplicateCluster",
        back_populates="members",
    )
    report: Mapped["WeatherReport"] = relationship(
        "WeatherReport",
        back_populates="duplicate_memberships",
    )
