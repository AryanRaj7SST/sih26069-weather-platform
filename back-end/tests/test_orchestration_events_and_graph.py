"""Unit tests for orchestration event schemas, dependency graph, state, and retry policy."""

import uuid
from typing import Dict

import httpx
import pytest
from pydantic import ValidationError

from app.intelligence.schemas import (
    DigitalEvidenceGroupInput,
    IncidentCredibilityInputs,
    PhysicalStationInput,
    SourceFamily,
)
from app.orchestration.dependency_graph import DependencyGraph
from app.orchestration.events import (
    AggregateType,
    FailureClass,
    OrchestrationEvent,
    OrchestrationEventType,
    OverallReadiness,
    StageName,
    StageOutcome,
)
from app.orchestration.handlers import compute_credibility_fingerprint
from app.orchestration.models import StageStateModel
from app.orchestration.retry_policy import RetryPolicy
from app.orchestration.state import derive_overall_readiness


def test_orchestration_event_schema_validation() -> None:
    """Verify strongly-typed event contract and rejection of unknown fields."""
    event_id = uuid.uuid4()
    agg_id = uuid.uuid4()

    event = OrchestrationEvent(
        event_id=event_id,
        event_type=OrchestrationEventType.INCIDENT_INGESTED,
        aggregate_type=AggregateType.WEATHER_REPORT,
        aggregate_id=agg_id,
        producer="ingestion_worker",
        correlation_id="corr-12345",
        idempotency_key=f"inc:{agg_id}:v1",
        payload={"tracking_id": "RPT-20260829-ABCD"},
    )

    assert event.event_id == event_id
    assert event.attempt == 1
    assert event.max_attempts == 3

    # Verify extra field rejection
    with pytest.raises(ValidationError):
        OrchestrationEvent(
            event_id=event_id,
            event_type=OrchestrationEventType.INCIDENT_INGESTED,
            aggregate_type=AggregateType.WEATHER_REPORT,
            aggregate_id=agg_id,
            producer="test",
            correlation_id="corr-123",
            idempotency_key="key",
            unknown_injected_field="malicious_payload",  # type: ignore[call-arg]
        )


def test_dependency_graph_prerequisites() -> None:
    """Verify hard dependencies vs optional enrichment semantics."""
    empty_stages: Dict[StageName, StageStateModel] = {}

    # LOCATION has no prerequisites
    assert DependencyGraph.can_execute_stage(StageName.LOCATION, empty_stages) is True

    # DUPLICATE, EVIDENCE, OBSERVATION require LOCATION
    assert DependencyGraph.can_execute_stage(StageName.DUPLICATE, empty_stages) is False
    assert DependencyGraph.can_execute_stage(StageName.EVIDENCE, empty_stages) is False
    assert DependencyGraph.can_execute_stage(StageName.OBSERVATION, empty_stages) is False

    # LOCATION complete (even with INSUFFICIENT_DATA) unblocks downstream stages
    stages_with_loc = {
        StageName.LOCATION: StageStateModel(status=StageOutcome.SUCCESS_WITH_INSUFFICIENT_DATA)
    }
    assert DependencyGraph.can_execute_stage(StageName.DUPLICATE, stages_with_loc) is True
    assert DependencyGraph.can_execute_stage(StageName.EVIDENCE, stages_with_loc) is True
    assert DependencyGraph.can_execute_stage(StageName.OBSERVATION, stages_with_loc) is True

    # CREDIBILITY is an optional aggregator; it can execute whenever called
    assert DependencyGraph.can_execute_stage(StageName.CREDIBILITY, empty_stages) is True


def test_derive_overall_readiness_states() -> None:
    """Verify derivation of overall intelligence readiness."""
    # 1. In-flight evaluation
    stages = {
        StageName.LOCATION: StageStateModel(status=StageOutcome.SUCCESS_WITH_RESULTS),
        StageName.DUPLICATE: StageStateModel(status=StageOutcome.SUCCESS_WITH_RESULTS),
    }
    assert derive_overall_readiness(stages) == OverallReadiness.INTELLIGENCE_PENDING

    # 2. Complete with all successes
    stages[StageName.EVIDENCE] = StageStateModel(status=StageOutcome.SUCCESS_WITH_RESULTS)
    stages[StageName.OBSERVATION] = StageStateModel(status=StageOutcome.SUCCESS_WITH_NO_MATCH)
    stages[StageName.CREDIBILITY] = StageStateModel(status=StageOutcome.SUCCESS_WITH_RESULTS)
    assert derive_overall_readiness(stages) == OverallReadiness.INTELLIGENCE_READY

    # 3. Partial readiness when optional stage is retrying
    stages[StageName.EVIDENCE] = StageStateModel(status=StageOutcome.RETRYABLE_FAILURE)
    assert derive_overall_readiness(stages) == OverallReadiness.INTELLIGENCE_PARTIAL

    # 4. Partial readiness when optional stage failed permanently
    stages[StageName.EVIDENCE] = StageStateModel(status=StageOutcome.PERMANENT_FAILURE)
    assert derive_overall_readiness(stages) == OverallReadiness.INTELLIGENCE_PARTIAL


def test_retry_policy_classification_and_backoff() -> None:
    """Verify retry policy correctly classifies errors and bounds backoff."""
    policy = RetryPolicy(base_delay_seconds=2.0, max_delay_seconds=30.0, max_attempts=3)

    # Transient errors
    timeout_err = httpx.ReadTimeout("Connection timeout to GDELT")
    assert policy.classify_error(timeout_err) == FailureClass.TRANSIENT
    assert policy.should_retry(attempt=1, exc=timeout_err) is True
    assert policy.should_retry(attempt=3, exc=timeout_err) is False  # Max reached

    # Permanent errors
    val_err = ValueError("Invalid schema payload")
    assert policy.classify_error(val_err) == FailureClass.PERMANENT
    assert policy.should_retry(attempt=1, exc=val_err) is False

    # Backoff progression
    b1 = policy.calculate_backoff_seconds(attempt=1)
    b2 = policy.calculate_backoff_seconds(attempt=2)
    b3 = policy.calculate_backoff_seconds(attempt=3)

    assert 1.0 <= b1 <= 3.0
    assert 2.5 <= b2 <= 5.5
    assert 5.0 <= b3 <= 10.0


def test_deterministic_input_fingerprint_sensitivity() -> None:
    """Verify input fingerprint changes on any material data modification."""
    inc_id = uuid.uuid4()
    base_inputs = IncidentCredibilityInputs(
        incident_id=inc_id,
        source_code="CITIZEN_WEB",
        source_type="CITIZEN_REPORT",
        source_base_trust=0.60,
        origin_family=SourceFamily.CITIZEN,
        has_coordinates=True,
        has_timestamp=True,
        has_location_name=True,
        has_description=True,
        has_category=True,
        cluster_member_count=1,
    )

    fp1 = compute_credibility_fingerprint(base_inputs)
    fp1_dup = compute_credibility_fingerprint(base_inputs)
    assert fp1 == fp1_dup  # Idempotent & deterministic

    # Change 1: Add evidence group
    inputs_with_evidence = base_inputs.model_copy(
        update={
            "evidence_groups": [
                DigitalEvidenceGroupInput(
                    provenance_key="domain_thehindu.com",
                    max_confidence=0.80,
                    role_weight=1.0,
                    article_count=1,
                    source_family=SourceFamily.NEWS,
                )
            ]
        }
    )
    fp2 = compute_credibility_fingerprint(inputs_with_evidence)
    assert fp1 != fp2

    # Change 2: Modify confidence score
    inputs_with_higher_conf = base_inputs.model_copy(
        update={
            "evidence_groups": [
                DigitalEvidenceGroupInput(
                    provenance_key="domain_thehindu.com",
                    max_confidence=0.90,
                    role_weight=1.0,
                    article_count=1,
                    source_family=SourceFamily.NEWS,
                )
            ]
        }
    )
    fp3 = compute_credibility_fingerprint(inputs_with_higher_conf)
    assert fp2 != fp3

    # Change 3: Add physical station corroboration
    inputs_with_obs = base_inputs.model_copy(
        update={
            "observation_stations": [
                PhysicalStationInput(
                    station_key="cwc_bhad_01",
                    corroboration_score=0.85,
                    relationship_weight=1.0,
                    source_family=SourceFamily.SENSOR,
                    points_count=24,
                )
            ]
        }
    )
    fp4 = compute_credibility_fingerprint(inputs_with_obs)
    assert fp1 != fp4
    assert fp2 != fp4
