import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.corroboration import IncidentObservationCorroboration
    from app.models.source import Source


class WeatherObservation(Base):
    __tablename__ = "weather_observations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
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
    station_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    station_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    geom: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True),
        nullable=False,
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    temperature_c: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    humidity_pct: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    rainfall_mm: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    water_level_m: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    wind_speed_kmh: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    wind_direction_deg: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    pressure_hpa: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    raw_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    source: Mapped["Source"] = relationship(
        "Source",
        back_populates="weather_observations",
    )
    corroborations: Mapped[List["IncidentObservationCorroboration"]] = relationship(
        "IncidentObservationCorroboration",
        back_populates="observation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_weather_observations_source_external", "source_id", "external_id"),
        Index(
            "idx_weather_observations_station_time",
            "station_code",
            observed_at.desc(),
        ),
    )
