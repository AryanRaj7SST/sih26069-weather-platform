"""Pydantic data models for orchestration stage states and pipeline telemetry.

Persisted within WeatherReport.raw_payload["orchestration"] to guarantee
durable, observable, per-stage execution histories without schema migrations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.orchestration.events import (
    FailureClass,
    OverallReadiness,
    StageName,
    StageOutcome,
)


class StageStateModel(BaseModel):
    """Execution telemetry and status for a single intelligence stage."""

    model_config = ConfigDict(extra="forbid")

    status: StageOutcome = Field(
        default=StageOutcome.SUCCESS_WITH_NO_MATCH,
        description="Current outcome state of this stage.",
    )
    attempt: int = Field(default=0, ge=0, description="Number of attempts made.")
    fingerprint: Optional[str] = Field(
        default=None, description="SHA256 fingerprint of input data processed."
    )
    started_at: Optional[datetime] = Field(
        default=None, description="UTC timestamp when stage started."
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="UTC timestamp when stage completed."
    )
    duration_ms: Optional[float] = Field(
        default=None, ge=0.0, description="Duration in milliseconds."
    )
    next_retry_at: Optional[datetime] = Field(
        default=None, description="Scheduled retry timestamp if in RETRY_WAIT."
    )
    error_class: FailureClass = Field(
        default=FailureClass.NONE, description="Classification of error if failed."
    )
    error_message: Optional[str] = Field(
        default=None, description="Sanitized error details if failed."
    )
    summary: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata summary of stage results."
    )


class PipelineOrchestrationState(BaseModel):
    """Complete orchestration document hosted inside WeatherReport.raw_payload['orchestration']."""

    model_config = ConfigDict(extra="forbid")

    version: str = Field(default="v1", description="Orchestration schema version.")
    overall_readiness: OverallReadiness = Field(
        default=OverallReadiness.INTELLIGENCE_PENDING,
        description="Aggregated intelligence readiness state.",
    )
    last_successful_stage: Optional[StageName] = Field(
        default=None, description="Most recently completed successful stage."
    )
    last_updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of last stage update.",
    )
    stages: Dict[StageName, StageStateModel] = Field(
        default_factory=dict,
        description="Per-stage independent execution states.",
    )


class DeadLetterJob(BaseModel):
    """Enriched envelope for failed events routed to the Dead Letter Queue."""

    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(..., description="Original message/event identifier.")
    event_type: str = Field(..., description="Event type of failed job.")
    aggregate_type: str = Field(..., description="Target aggregate entity type.")
    aggregate_id: str = Field(..., description="Primary key of entity.")
    attempt: int = Field(..., description="Total attempts made before dead-lettering.")
    first_failed_at: datetime = Field(..., description="Initial failure timestamp.")
    dead_lettered_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp routed to DLQ.",
    )
    error_class: str = Field(..., description="Class of error (TRANSIENT / PERMANENT).")
    error_message: str = Field(..., description="Sanitized root failure reason.")
    stage_name: Optional[str] = Field(default=None, description="Failed stage if known.")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event payload.")
    is_replayed: bool = Field(default=False, description="True if replayed by operator.")
