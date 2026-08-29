import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Float, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.ingestion import IngestionRun
    from app.models.observation import WeatherObservation
    from app.models.report import WeatherReport


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    base_trust_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    weather_reports: Mapped[List["WeatherReport"]] = relationship(
        "WeatherReport",
        back_populates="source",
    )
    weather_observations: Mapped[List["WeatherObservation"]] = relationship(
        "WeatherObservation",
        back_populates="source",
    )
    ingestion_runs: Mapped[List["IngestionRun"]] = relationship(
        "IngestionRun",
        back_populates="source",
    )
