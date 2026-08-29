import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class RawIngestionEvent(BaseModel):
    """Raw, un-normalized observation or alert payload from an external or internal source."""

    source_code: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Catalog code of originating source (e.g. 'CITIZEN_WEB', 'IMD_AWS').",
    )
    external_id: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Source-provided unique item identifier (e.g. RSS GUID).",
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Raw, heterogeneous source payload.",
    )
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the raw event was captured.",
    )


class NormalizedIngestionEvent(BaseModel):
    """Standardized, validated event representation consumed across the platform pipeline."""

    event_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique pipeline event identifier.",
    )
    source_code: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Originating source catalog code.",
    )
    external_id: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Unique source identifier for deduplication and idempotency.",
    )
    category_code: Optional[str] = Field(
        default="OTHER",
        max_length=50,
        description="Standardized hazard category code.",
    )
    severity: str = Field(
        default="MODERATE",
        description="Standardized event severity level.",
    )
    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Cleaned, human-readable event title.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Detailed event description.",
    )
    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="WGS84 decimal latitude.",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="WGS84 decimal longitude.",
    )
    location_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Human-readable landmark or district name.",
    )
    occurred_at: datetime = Field(
        ...,
        description="Time when the event occurred (UTC).",
    )
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Pipeline ingestion timestamp (UTC).",
    )
    raw_payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Preserved raw source payload for audit and reprocessing.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional pipeline and adapter metadata.",
    )

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        upper_v = v.upper().strip()
        if upper_v == "CRITICAL":
            return "SEVERE"
        valid = {"LOW", "MODERATE", "HIGH", "SEVERE"}
        if upper_v not in valid:
            return "MODERATE"
        return upper_v

    @field_validator("occurred_at", "ingested_at")
    @classmethod
    def ensure_utc_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)


class NormalizedObservationEvent(BaseModel):
    """Standardized physical sensor telemetry representation consumed across the platform."""

    event_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique pipeline event identifier.",
    )
    source_code: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Originating source catalog code (e.g. 'CWC_NWDP', 'IMD_AWS').",
    )
    external_id: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Unique station-time observation identifier for deduplication and idempotency.",
    )
    station_code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Stable station code identifier.",
    )
    station_name: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Human-readable station name.",
    )
    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="WGS84 decimal latitude.",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="WGS84 decimal longitude.",
    )
    observed_at: datetime = Field(
        ...,
        description="Time when the sensor measurement was taken (UTC).",
    )
    water_level_m: Optional[float] = Field(
        default=None,
        description="River or reservoir water elevation in meters.",
    )
    rainfall_mm: Optional[float] = Field(
        default=None,
        description="Precipitation accumulation in millimeters.",
    )
    temperature_c: Optional[float] = Field(
        default=None,
        description="Ambient air temperature in Celsius.",
    )
    humidity_pct: Optional[float] = Field(
        default=None,
        description="Relative humidity percentage.",
    )
    wind_speed_kmh: Optional[float] = Field(
        default=None,
        description="Wind speed in km/h.",
    )
    wind_direction_deg: Optional[int] = Field(
        default=None,
        ge=0,
        le=360,
        description="Wind direction in degrees (0-360).",
    )
    pressure_hpa: Optional[float] = Field(
        default=None,
        description="Atmospheric pressure in hectopascals.",
    )
    raw_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Source-specific telemetry metadata.",
    )
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Pipeline ingestion timestamp (UTC).",
    )

    @field_validator("observed_at", "ingested_at")
    @classmethod
    def ensure_utc_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)
