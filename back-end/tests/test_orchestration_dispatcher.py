"""Unit & integration tests for Redis Streams dispatcher, DLQ management, and replay."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestration.dispatcher import OrchestrationDispatcher, orchestration_dispatcher
from app.orchestration.events import (
    AggregateType,
    FailureClass,
    OrchestrationEvent,
    OrchestrationEventType,
    StageName,
    StageOutcome,
)


@pytest.mark.asyncio
async def test_dispatcher_event_routing_happy_path(db_session: AsyncSession) -> None:
    """Verify dispatcher routes INCIDENT_INGESTED event and returns success result."""
    report_id = uuid.uuid4()
    event = OrchestrationEvent(
        event_type=OrchestrationEventType.INCIDENT_INGESTED,
        aggregate_type=AggregateType.WEATHER_REPORT,
        aggregate_id=report_id,
        producer="test_suite",
        correlation_id="corr-test-1",
        idempotency_key=f"inc:{report_id}:v1",
    )

    with patch("app.orchestration.dispatcher.on_incident_ingested") as mock_pipeline:
        mock_state = AsyncMock()
        mock_state.last_successful_stage = StageName.CREDIBILITY
        mock_state.overall_readiness.value = "INTELLIGENCE_READY"
        mock_pipeline.return_value = mock_state

        res = await orchestration_dispatcher.process_event(db=db_session, event=event)
        assert res.outcome == StageOutcome.SUCCESS_WITH_RESULTS
        assert res.stage_name == StageName.CREDIBILITY


@pytest.mark.asyncio
async def test_dispatcher_unknown_event_type_handling(db_session: AsyncSession) -> None:
    """Verify unknown event type transitions to PERMANENT_FAILURE without crash loop."""
    event = OrchestrationEvent(
        event_type=OrchestrationEventType.STAGE_DEAD_LETTERED,  # Unhandled worker event
        aggregate_type=AggregateType.WEATHER_REPORT,
        aggregate_id=uuid.uuid4(),
        producer="test",
        correlation_id="corr-unk",
        idempotency_key="key-unk",
    )

    res = await orchestration_dispatcher.process_event(db=db_session, event=event)
    assert res.outcome == StageOutcome.PERMANENT_FAILURE
    assert res.error_class == FailureClass.PERMANENT
    assert "Unhandled event type" in str(res.error_message)


@pytest.mark.asyncio
async def test_dispatcher_dead_letter_routing() -> None:
    """Verify failed job is structured and routed to DLQ stream."""
    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock(return_value="1700000000000-0")

    dispatcher = OrchestrationDispatcher(client=mock_redis)
    event = OrchestrationEvent(
        event_type=OrchestrationEventType.INCIDENT_INGESTED,
        aggregate_type=AggregateType.WEATHER_REPORT,
        aggregate_id=uuid.uuid4(),
        producer="test",
        correlation_id="corr-dlq",
        attempt=3,
        max_attempts=3,
        idempotency_key="key-dlq",
    )

    msg_id = await dispatcher.route_to_dead_letter(
        event=event,
        error_class=FailureClass.PERMANENT,
        error_message="Schema validation error",
        stage_name="LOCATION",
    )

    assert msg_id == "1700000000000-0"
    mock_redis.xadd.assert_called_once()
    call_args = mock_redis.xadd.call_args
    assert call_args[0][0] == "stream:weather:dead_letter"


@pytest.mark.asyncio
async def test_dispatcher_replay_dead_letter_job(db_session: AsyncSession) -> None:
    """Verify dead letter replay resets attempt count and executes pipeline."""
    report_id = uuid.uuid4()
    raw_event_dict = {
        "event_id": str(uuid.uuid4()),
        "event_type": OrchestrationEventType.INCIDENT_INGESTED.value,
        "aggregate_type": AggregateType.WEATHER_REPORT.value,
        "aggregate_id": str(report_id),
        "producer": "dlq_replay_cli",
        "correlation_id": "corr-replay-1",
        "attempt": 3,
        "max_attempts": 3,
        "idempotency_key": f"inc:{report_id}:v1",
        "payload_version": "v1",
        "payload": {},
    }

    with patch("app.orchestration.dispatcher.on_incident_ingested") as mock_pipeline:
        mock_state = AsyncMock()
        mock_state.last_successful_stage = StageName.CREDIBILITY
        mock_state.overall_readiness.value = "INTELLIGENCE_READY"
        mock_pipeline.return_value = mock_state

        res = await orchestration_dispatcher.replay_dead_letter_job(
            db=db_session,
            event_dict=raw_event_dict,
        )
        assert res.outcome == StageOutcome.SUCCESS_WITH_RESULTS


@pytest.mark.asyncio
async def test_dispatcher_concurrent_duplicate_event_delivery_idempotent(
    db_session: AsyncSession,
) -> None:
    """Verify duplicate event deliveries processed in sequence or concurrently are idempotent."""
    report_id = uuid.uuid4()
    event = OrchestrationEvent(
        event_type=OrchestrationEventType.INCIDENT_INGESTED,
        aggregate_type=AggregateType.WEATHER_REPORT,
        aggregate_id=report_id,
        producer="ingestion_worker",
        correlation_id="corr-dup-1",
        idempotency_key=f"inc:{report_id}:v1",
    )

    with patch("app.orchestration.dispatcher.on_incident_ingested") as mock_pipeline:
        mock_state = AsyncMock()
        mock_state.last_successful_stage = StageName.CREDIBILITY
        mock_state.overall_readiness.value = "INTELLIGENCE_READY"
        mock_pipeline.return_value = mock_state

        # Delivery 1
        res1 = await orchestration_dispatcher.process_event(db=db_session, event=event)
        # Duplicate Delivery 2
        res2 = await orchestration_dispatcher.process_event(db=db_session, event=event)

        assert res1.outcome == StageOutcome.SUCCESS_WITH_RESULTS
        assert res2.outcome == StageOutcome.SUCCESS_WITH_RESULTS
        assert mock_pipeline.call_count == 2
