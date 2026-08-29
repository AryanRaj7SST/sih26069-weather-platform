import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from geoalchemy2 import Geometry
from sqlalchemy import (
    ARRAY,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.category import EventCategory
    from app.models.duplicate import DuplicateCluster, DuplicateMember
    from app.models.media import ReportMedia
    from app.models.source import Source
    from app.models.verification import VerificationEvent


class WeatherReport(Base):
    __tablename__ = "weather_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tracking_id: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id"),
        nullable=False,
    )
    external_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_categories.id"),
        nullable=True,
    )
    reported_category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="MODERATE",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    location_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    geom: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True),
        nullable=False,
    )
    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    processing_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING",
    )
    verification_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING",
        index=True,
    )
    credibility_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        index=True,
    )
    credibility_explanation: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    text_embedding: Mapped[Optional[List[float]]] = mapped_column(
        ARRAY(Float),
        nullable=True,
    )
    raw_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    source: Mapped["Source"] = relationship(
        "Source",
        back_populates="weather_reports",
    )
    category: Mapped[Optional["EventCategory"]] = relationship(
        "EventCategory",
        back_populates="weather_reports",
    )
    media: Mapped[List["ReportMedia"]] = relationship(
        "ReportMedia",
        back_populates="report",
        cascade="all, delete-orphan",
    )
    verification_events: Mapped[List["VerificationEvent"]] = relationship(
        "VerificationEvent",
        back_populates="report",
    )
    duplicate_memberships: Mapped[List["DuplicateMember"]] = relationship(
        "DuplicateMember",
        back_populates="report",
        cascade="all, delete-orphan",
    )
    primary_cluster: Mapped[Optional["DuplicateCluster"]] = relationship(
        "DuplicateCluster",
        back_populates="primary_report",
        foreign_keys="DuplicateCluster.primary_report_id",
    )

    __table_args__ = (
        Index("idx_weather_reports_status_time", "verification_status", occurred_at.desc()),
        Index("idx_weather_reports_credibility", credibility_score.desc()),
        Index("idx_weather_reports_source_external", "source_id", "external_id"),
    )
