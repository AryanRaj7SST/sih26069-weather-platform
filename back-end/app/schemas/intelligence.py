"""Pydantic schemas for orchestration and intelligence status response contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.orchestration.events import OverallReadiness, StageOutcome


class StageStatusSummary(BaseModel):
    """Safe, high-level status of a single intelligence pipeline stage."""

    model_config = ConfigDict(from_attributes=True)

    status: StageOutcome = Field(..., description="Stage terminal or intermediate status.")
    attempt: int = Field(default=1, ge=0, description="Execution attempt count.")
    duration_ms: Optional[float] = Field(
        default=None, description="Stage duration in milliseconds."
    )
    error_message: Optional[str] = Field(default=None, description="Sanitized failure description.")
    summary: Dict[str, Any] = Field(
        default_factory=dict, description="Stage result metrics summary."
    )


class IncidentIntelligenceData(BaseModel):
    """Operational intelligence readiness and per-stage pipeline state."""

    model_config = ConfigDict(from_attributes=True)

    incident_id: uuid.UUID
    overall_readiness: OverallReadiness = Field(
        ...,
        description="Readiness: INTELLIGENCE_READY, INTELLIGENCE_PARTIAL, PENDING, FAILED.",
    )
    last_successful_stage: Optional[str] = Field(
        default=None,
        description="Most recently completed pipeline stage.",
    )
    last_computed_at: datetime = Field(
        ...,
        description="Timestamp when intelligence orchestration last completed an evaluation.",
    )
    stages: Dict[str, StageStatusSummary] = Field(
        default_factory=dict,
        description="Per-stage execution telemetry map.",
    )


class IncidentIntelligenceStatusResponse(BaseModel):
    """Standard API envelope for intelligence readiness status."""

    success: bool = True
    data: IncidentIntelligenceData
    meta: dict = Field(default_factory=dict)
