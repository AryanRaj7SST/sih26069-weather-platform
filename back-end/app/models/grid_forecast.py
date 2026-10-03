import uuid
from datetime import datetime
from typing import Any, Optional

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WeatherGridForecast(Base):
    __tablename__ = "weather_grid_forecast"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    valid_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    temperature_2m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    precipitation: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wind_speed_10m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wind_direction_10m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pressure_msl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    geom: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True),
        nullable=False,
    )
    source_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="OPEN_METEO",
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("latitude", "longitude", "valid_time", name="uq_weather_grid_forecast_lat_lon_time"),
        Index("idx_weather_grid_forecast_lat_lon", "latitude", "longitude"),
    )


class MarineGridForecast(Base):
    __tablename__ = "marine_grid_forecast"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    valid_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    wave_height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wave_direction: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wave_period: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    geom: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True),
        nullable=False,
    )
    source_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="OPEN_METEO_MARINE",
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("latitude", "longitude", "valid_time", name="uq_marine_grid_forecast_lat_lon_time"),
        Index("idx_marine_grid_forecast_lat_lon", "latitude", "longitude"),
    )
