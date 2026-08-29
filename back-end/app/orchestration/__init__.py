"""High-assurance end-to-end intelligence orchestration package.

Coordinates location resolution, duplicate clustering, evidence linking,
observation corroboration, and credibility scoring with failure isolation,
idempotency, and targeted incremental triggers.
"""

from app.orchestration.dependency_graph import DependencyGraph
from app.orchestration.dispatcher import (
    OrchestrationDispatcher,
    orchestration_dispatcher,
)
from app.orchestration.events import (
    AggregateType,
    FailureClass,
    OrchestrationEvent,
    OrchestrationEventType,
    OverallReadiness,
    StageExecutionResult,
    StageName,
    StageOutcome,
)
from app.orchestration.handlers import (
    CredibilityStageHandler,
    DuplicateStageHandler,
    EvidenceStageHandler,
    LocationStageHandler,
    ObservationStageHandler,
    compute_credibility_fingerprint,
    credibility_stage_handler,
    duplicate_stage_handler,
    evidence_stage_handler,
    location_stage_handler,
    observation_stage_handler,
)
from app.orchestration.incident_pipeline import (
    IncidentPipeline,
    incident_pipeline,
)
from app.orchestration.models import (
    DeadLetterJob,
    PipelineOrchestrationState,
    StageStateModel,
)
from app.orchestration.retry_policy import (
    RetryPolicy,
    retry_policy,
)
from app.orchestration.state import (
    derive_overall_readiness,
    load_orchestration_state,
    update_stage_state,
)
from app.orchestration.triggers import (
    on_duplicate_cluster_updated,
    on_evidence_ingested,
    on_human_verification_updated,
    on_incident_ingested,
    on_observation_ingested,
)

__all__ = [
    "DependencyGraph",
    "OrchestrationDispatcher",
    "orchestration_dispatcher",
    "AggregateType",
    "FailureClass",
    "OrchestrationEvent",
    "OrchestrationEventType",
    "OverallReadiness",
    "StageExecutionResult",
    "StageName",
    "StageOutcome",
    "LocationStageHandler",
    "location_stage_handler",
    "DuplicateStageHandler",
    "duplicate_stage_handler",
    "EvidenceStageHandler",
    "evidence_stage_handler",
    "ObservationStageHandler",
    "observation_stage_handler",
    "CredibilityStageHandler",
    "credibility_stage_handler",
    "compute_credibility_fingerprint",
    "IncidentPipeline",
    "incident_pipeline",
    "DeadLetterJob",
    "PipelineOrchestrationState",
    "StageStateModel",
    "RetryPolicy",
    "retry_policy",
    "derive_overall_readiness",
    "load_orchestration_state",
    "update_stage_state",
    "on_incident_ingested",
    "on_evidence_ingested",
    "on_observation_ingested",
    "on_duplicate_cluster_updated",
    "on_human_verification_updated",
]
