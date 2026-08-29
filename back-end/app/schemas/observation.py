"""Pydantic schemas for physical observation corroboration response contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.intelligence.schemas import ObservationRelationship
from app.schemas.report import PaginationMeta


class ObservationMetricSummary(BaseModel):
    """Telemetry readings recorded by the physical monitoring station."""

    model_config = ConfigDict(from_attributes=True)

    rainfall_mm_1h: Optional[float] = Field(
        default=None, description="1-hour accumulated rainfall (mm)."
    )
    rainfall_mm_24h: Optional[float] = Field(
        default=None, description="24-hour accumulated rainfall (mm)."
    )
    water_level_m: Optional[float] = Field(
        default=None, description="River/reservoir water level (meters)."
    )
    flood_status: Optional[str] = Field(
        default=None, description="Official flood stage classification."
    )
    wind_speed_kmh: Optional[float] = Field(
        default=None, description="Sustained wind speed (km/h)."
    )


class IncidentObservationItemData(BaseModel):
    """Physical weather/hydrological observation corroborating an incident."""

    model_config = ConfigDict(from_attributes=True)

    corroboration_id: uuid.UUID = Field(..., description="Unique corroboration relationship ID.")
    observation_id: uuid.UUID = Field(..., description="Source observation telemetry ID.")
    station_code: str = Field(..., description="Unique station code (e.g., IMD_BOM_04).")
    station_name: Optional[str] = Field(default=None, description="Station human-readable name.")
    source_code: str = Field(..., description="Originating network (IMD_AWS, CWC_HYDRO, etc.).")
    observed_at: datetime = Field(..., description="Observation recorded timestamp.")
    distance_km: float = Field(
        ..., ge=0.0, description="Spatial distance to incident in kilometers."
    )
    relationship: ObservationRelationship = Field(
        ...,
        description="Canonical relationship: CORROBORATING, CONSISTENT, WEAK, CONTRADICTORY, etc.",
    )
    corroboration_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Composite corroboration score.",
    )
    is_contradiction: bool = Field(
        default=False,
        description="True if sensor reading diagnostic contradicts incident claim.",
    )
    metrics: ObservationMetricSummary
    is_human_override: bool = Field(
        default=False,
        description="True if an operator manually confirmed this corroboration.",
    )


class IncidentObservationListResponse(BaseModel):
    """Standard API envelope for paginated incident observations."""

    success: bool = True
    data: List[IncidentObservationItemData] = Field(default_factory=list)
    pagination: PaginationMeta
    meta: dict = Field(default_factory=dict)
