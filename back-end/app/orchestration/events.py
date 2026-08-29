"""Typed event schemas and contracts for intelligence orchestration.

Enforces strict domain boundaries, correlation/causation tracking,
retry scheduling, and deterministic idempotency keys.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class OrchestrationEventType(str, enum.Enum):
    """Enumeration of domain and lifecycle orchestration events."""

    INCIDENT_INGESTED = "incident.ingested"
    LOCATION_STAGE_COMPLETED = "incident.location.completed"
    DUPLICATE_STAGE_COMPLETED = "incident.duplicate.completed"
    EVIDENCE_LINK_MODIFIED = "incident.evidence.modified"
    OBSERVATION_CORROBORATION_MODIFIED = "incident.observation.modified"
    DUPLICATE_CLUSTER_MODIFIED = "incident.cluster.modified"
    CREDIBILITY_STAGE_COMPLETED = "incident.credibility.completed"
    STAGE_RETRY_SCHEDULED = "orchestration.stage.retry"
    STAGE_DEAD_LETTERED = "orchestration.stage.dead_letter"
    SIGNAL_TRIGGERED = "orchestration.signal.triggered"


class AggregateType(str, enum.Enum):
    """Supported aggregate root types for orchestration."""

    WEATHER_REPORT = "WEATHER_REPORT"
    EVIDENCE_ITEM = "EVIDENCE_ITEM"
    WEATHER_OBSERVATION = "WEATHER_OBSERVATION"
    DUPLICATE_CLUSTER = "DUPLICATE_CLUSTER"


class StageName(str, enum.Enum):
    """Names of distinct intelligence pipeline stages."""

    LOCATION = "LOCATION"
    DUPLICATE = "DUPLICATE"
    EVIDENCE = "EVIDENCE"
    OBSERVATION = "OBSERVATION"
    CREDIBILITY = "CREDIBILITY"


class StageOutcome(str, enum.Enum):
    """Granular execution outcomes for individual pipeline stages."""

    SUCCESS_WITH_RESULTS = "SUCCESS_WITH_RESULTS"
    SUCCESS_WITH_NO_MATCH = "SUCCESS_WITH_NO_MATCH"
    SUCCESS_WITH_INSUFFICIENT_DATA = "SUCCESS_WITH_INSUFFICIENT_DATA"
    SKIPPED_NOT_APPLICABLE = "SKIPPED_NOT_APPLICABLE"
    SKIPPED_STALE = "SKIPPED_STALE"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    PERMANENT_FAILURE = "PERMANENT_FAILURE"


class OverallReadiness(str, enum.Enum):
    """Derived overall incident intelligence readiness state."""

    INTELLIGENCE_PENDING = "INTELLIGENCE_PENDING"
    INTELLIGENCE_READY = "INTELLIGENCE_READY"
    INTELLIGENCE_PARTIAL = "INTELLIGENCE_PARTIAL"
    INTELLIGENCE_FAILED = "INTELLIGENCE_FAILED"


class FailureClass(str, enum.Enum):
    """Classification of errors for retry decision logic."""

    TRANSIENT = "TRANSIENT"
    PERMANENT = "PERMANENT"
    NONE = "NONE"


class OrchestrationEvent(BaseModel):
    """Canonical event envelope for Redis Streams orchestration."""

    model_config = ConfigDict(extra="forbid")

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique event ID.")
    event_type: OrchestrationEventType = Field(..., description="Type of domain event.")
    aggregate_type: AggregateType = Field(..., description="Target aggregate entity type.")
    aggregate_id: uuid.UUID = Field(..., description="Primary key of target entity.")
    producer: str = Field(..., description="Originating service/worker name.")
    correlation_id: str = Field(..., description="Distributed tracing correlation ID.")
    causation_id: Optional[str] = Field(
        default=None, description="Event ID that directly triggered this event."
    )
    attempt: int = Field(default=1, ge=1, description="Current processing attempt number.")
    max_attempts: int = Field(default=3, ge=1, description="Maximum retry attempts allowed.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC event creation timestamp.",
    )
    scheduled_at: Optional[datetime] = Field(
        default=None, description="UTC timestamp after which this event may be processed."
    )
    idempotency_key: str = Field(..., description="Deterministic key preventing duplicate work.")
    payload_version: str = Field(default="v1", description="Payload schema version.")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event-specific payload.")


class StageExecutionResult(BaseModel):
    """Output summary returned by a single stage execution."""

    model_config = ConfigDict(extra="forbid")

    stage_name: StageName = Field(..., description="Executed stage name.")
    outcome: StageOutcome = Field(..., description="Granular execution outcome.")
    fingerprint: Optional[str] = Field(
        default=None, description="SHA256 fingerprint of input state evaluated."
    )
    duration_ms: float = Field(default=0.0, ge=0.0, description="Stage duration in milliseconds.")
    error_class: FailureClass = Field(
        default=FailureClass.NONE, description="Classification of failure if any."
    )
    error_message: Optional[str] = Field(default=None, description="Sanitized failure description.")
    results_summary: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata summary of stage output."
    )
    affected_incident_ids: List[uuid.UUID] = Field(
        default_factory=list, description="Downstream incident IDs needing recomputation."
    )
