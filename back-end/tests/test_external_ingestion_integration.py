"""Integration tests for external data ingestion, multi-stream multiplexing, and runners."""

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import AsyncRedisClient
from app.ingestion.base import BaseIngestionAdapter
from app.ingestion.registry import AdapterRegistry
from app.ingestion.schemas import (
    NormalizedEvidenceEvent,
    NormalizedIngestionEvent,
    NormalizedObservationEvent,
    RawIngestionEvent,
)
from app.models.evidence import EvidenceItem
from app.models.observation import WeatherObservation
from app.models.outbox import RealtimeOutbox
from app.models.report import WeatherReport
from app.orchestration.dispatcher import OrchestrationDispatcher
from app.orchestration.events import (
    OrchestrationEvent,
    OrchestrationEventType,
    OverallReadiness,
)
from app.services.evidence_service import EvidenceService
from app.services.observation_service import ObservationService
from app.services.realtime_service import RealtimeService
from app.services.report_service import ReportService
from app.services.stream_service import StreamService
from app.workers.evidence_worker import EvidenceWorker
from app.workers.ingestion_worker import IngestionWorker
from app.workers.observation_worker import ObservationWorker
from app.workers.outbox_worker import RealtimeOutboxWorker
from app.workers.run_scheduler import trigger_ingestion_cycle

pytestmark = pytest.mark.asyncio


def _create_mock_stream_bus() -> Tuple[MagicMock, Dict[str, List[Tuple[str, Dict[str, Any]]]]]:
    """Create an in-memory Redis stream mock supporting multiple decoupled streams."""
    mock_redis = MagicMock(spec=AsyncRedisClient)
    stream_store: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {
        "stream:weather:events": [],
        "stream:weather:observations": [],
        "stream:weather:evidence": [],
        "stream:weather:orchestration": [],
        "stream:weather:realtime": [],
    }

    async def mock_xadd(stream: str, fields: Dict[str, Any], **kwargs: Any) -> str:
        if stream not in stream_store:
            stream_store[stream] = []
        msg_id = f"1725000000000-{len(stream_store[stream]) + 1}"
        stream_store[stream].append((msg_id, fields))
        return msg_id

    mock_redis.xadd = AsyncMock(side_effect=mock_xadd)
    mock_redis.xgroup_create = AsyncMock(return_value=True)

    async def mock_xreadgroup(
        group: str,
        consumer: str,
        streams: Dict[str, str],
        count: int = 10,
        block_ms: int | None = None,
        **kwargs: Any,
    ) -> List[Tuple[str, List[Tuple[str, Dict[str, Any]]]]]:
        results = []
        for s in streams.keys():
            entries = stream_store.get(s, [])
            if entries:
                results.append((s, list(entries)))
        return results

    mock_redis.xreadgroup = AsyncMock(side_effect=mock_xreadgroup)
    mock_redis.xack = AsyncMock(return_value=1)

    return mock_redis, stream_store


class MultiTypeMockAdapter(BaseIngestionAdapter):
    """Mock adapter returning a mixture of Ingestion, Observation, and Evidence events."""

    def __init__(self) -> None:
        super().__init__(
            source_code="TEST_MULTI",
            source_name="Multi-Type Ingestion Test Feed",
        )

    async def fetch_raw_events(self) -> List[RawIngestionEvent]:
        return []

    async def ingest(self) -> List[Any]:
        now = datetime.now(timezone.utc)
        return [
            NormalizedIngestionEvent(
                source_code="TEST_MULTI",
                external_id="INCIDENT-001",
                category_code="FLOOD_WATERLOGGING",
                severity="HIGH",
                title="Severe Flooding in Dadar",
                description="Water accumulation on road.",
                location_name="Dadar, Mumbai",
                latitude=19.0178,
                longitude=72.8478,
                occurred_at=now,
            ),
            NormalizedObservationEvent(
                source_code="TEST_MULTI",
                external_id="OBS-001",
                station_code="CWC-KRISHNA-01",
                station_name="Krishna River Gauge",
                latitude=16.5062,
                longitude=80.6480,
                observed_at=now,
                water_level_m=54.2,
                raw_metrics={"river": "Krishna"},
            ),
            NormalizedEvidenceEvent(
                source_code="TEST_MULTI",
                external_id="EVID-001",
                evidence_type="NEWS_ARTICLE",
                title="NDRF teams deployed in flood-affected districts",
                url="https://news.example.com/ndrf-flood",
                publisher_domain="news.example.com",
                published_at=now,
                text_snippet="Rescue operations ongoing.",
            ),
        ]


async def test_scheduler_multi_stream_routing() -> None:
    """Proves run_scheduler routes Ingestion, Observation, and Evidence to streams."""
    mock_redis, streams = _create_mock_stream_bus()
    mock_stream_svc = StreamService(client=mock_redis)

    test_registry = AdapterRegistry()
    test_adapter = MultiTypeMockAdapter()
    test_registry.register(test_adapter)

    with (
        patch("app.workers.run_scheduler.adapter_registry", test_registry),
        patch("app.workers.run_scheduler.stream_service", mock_stream_svc),
    ):
        await trigger_ingestion_cycle()

    # 1. Verify stream:weather:events received the incident event
    event_stream_entries = streams["stream:weather:events"]
    assert len(event_stream_entries) == 1
    assert event_stream_entries[0][1]["external_id"] == "INCIDENT-001"
    assert event_stream_entries[0][1]["category_code"] == "FLOOD_WATERLOGGING"

    # 2. Verify stream:weather:observations received the observation event
    obs_stream_entries = streams["stream:weather:observations"]
    assert len(obs_stream_entries) == 1
    assert obs_stream_entries[0][1]["station_code"] == "CWC-KRISHNA-01"

    # 3. Verify stream:weather:evidence received the evidence event
    ev_stream_entries = streams["stream:weather:evidence"]
    assert len(ev_stream_entries) == 1
    assert ev_stream_entries[0][1]["domain"] == "news.example.com"


async def test_ingestion_worker_batch_and_loop_cancellation(db_session: AsyncSession) -> None:
    """Proves IngestionWorker consumes from stream:weather:events and cancels cleanly."""
    mock_redis, streams = _create_mock_stream_bus()
    mock_stream_svc = StreamService(client=mock_redis)

    now = datetime.now(timezone.utc)
    ingest_event = NormalizedIngestionEvent(
        source_code="TEST_INGEST",
        external_id=f"EXT-{uuid.uuid4().hex[:6]}",
        category_code="HEAVY_RAINFALL",
        severity="SEVERE",
        title="Torrential Rainfall in Santacruz",
        description="Rainfall intensity exceeding 50mm/hr.",
        location_name="Santacruz, Mumbai",
        latitude=19.0800,
        longitude=72.8400,
        occurred_at=now,
    )

    # Publish to in-memory stream
    await mock_stream_svc.publish_event(ingest_event)
    assert len(streams["stream:weather:events"]) == 1

    @asynccontextmanager
    async def session_factory() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    # Worker consumes batch
    worker = IngestionWorker(
        stream_svc=mock_stream_svc,
        session_factory=session_factory,  # type: ignore[arg-type]
    )
    results = await worker.process_batch(count=10)
    assert len(results) == 1
    msg_id, report = results[0]
    assert report is not None
    assert report.processing_status == "QUEUED"

    # Verify run_loop stops cleanly on stop_event
    stop_event = asyncio.Event()
    stop_event.set()
    await worker.run_loop(stop_event=stop_event, interval=0.01)

    # Cleanup created report
    await db_session.execute(
        delete(RealtimeOutbox).where(RealtimeOutbox.entity_id == str(report.id))
    )
    await db_session.execute(delete(WeatherReport).where(WeatherReport.id == report.id))
    await db_session.commit()


async def test_ingestion_worker_failure_isolation(db_session: AsyncSession) -> None:
    """Proves a failure in one event does not block processing of subsequent valid events."""
    mock_redis, streams = _create_mock_stream_bus()
    mock_stream_svc = StreamService(client=mock_redis)

    now = datetime.now(timezone.utc)
    event1 = NormalizedIngestionEvent(
        source_code="TEST_FAIL_ISO",
        external_id=f"EXT-FAIL-{uuid.uuid4().hex[:6]}",
        category_code="HEAVY_RAINFALL",
        severity="SEVERE",
        title="Valid Event 1",
        description="Description 1",
        location_name="Location 1",
        latitude=19.0800,
        longitude=72.8400,
        occurred_at=now,
    )
    event2 = NormalizedIngestionEvent(
        source_code="TEST_FAIL_ISO",
        external_id=f"EXT-FAIL-{uuid.uuid4().hex[:6]}",
        category_code="HEAVY_RAINFALL",
        severity="SEVERE",
        title="Valid Event 2",
        description="Description 2",
        location_name="Location 2",
        latitude=19.0800,
        longitude=72.8400,
        occurred_at=now,
    )

    await mock_stream_svc.publish_event(event1)
    await mock_stream_svc.publish_event(event2)

    @asynccontextmanager
    async def session_factory() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    call_count = 0
    real_process = IngestionWorker.process_event

    async def mock_process(
        self: Any, session: AsyncSession, event: NormalizedIngestionEvent
    ) -> WeatherReport:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Simulated transient processing error")
        return await real_process(self, session, event)

    worker = IngestionWorker(
        stream_svc=mock_stream_svc,
        session_factory=session_factory,  # type: ignore[arg-type]
    )

    with patch.object(IngestionWorker, "process_event", mock_process):
        results = await worker.process_batch(count=10)

    # First message failed (None), second succeeded
    assert len(results) == 2
    assert results[0][1] is None
    assert results[1][1] is not None
    assert results[1][1].title == "Valid Event 2"

    # Cleanup
    await db_session.execute(
        delete(RealtimeOutbox).where(RealtimeOutbox.entity_id == str(results[1][1].id))
    )
    await db_session.execute(delete(WeatherReport).where(WeatherReport.id == results[1][1].id))
    await db_session.commit()


async def test_external_event_deduplication(db_session: AsyncSession) -> None:
    """Proves ingesting the same (source_code, external_id) twice deduplicates cleanly."""
    mock_redis, _ = _create_mock_stream_bus()
    mock_realtime = RealtimeService(client=mock_redis)
    report_svc = ReportService(realtime_svc=mock_realtime)

    unique_ext_id = f"DEDUP-{uuid.uuid4().hex[:6]}"
    now = datetime.now(timezone.utc)
    event1 = NormalizedIngestionEvent(
        source_code="TEST_DEDUP",
        external_id=unique_ext_id,
        category_code="FLOOD_WATERLOGGING",
        severity="HIGH",
        title="Initial External Report",
        description="Initial payload.",
        location_name="Bandra, Mumbai",
        latitude=19.0596,
        longitude=72.8295,
        occurred_at=now,
    )

    # First ingestion creates report
    report1 = await report_svc.ingest_normalized_event(db_session, event1)
    report1_id = report1.id

    # Second ingestion with same external_id updates payload and returns same report
    event2 = NormalizedIngestionEvent(
        source_code="TEST_DEDUP",
        external_id=unique_ext_id,
        category_code="FLOOD_WATERLOGGING",
        severity="HIGH",
        title="Updated External Report",
        description="Updated payload with more details.",
        location_name="Bandra, Mumbai",
        latitude=19.0596,
        longitude=72.8295,
        occurred_at=now,
    )
    report2 = await report_svc.ingest_normalized_event(db_session, event2)
    assert report2.id == report1_id

    # Verify only 1 report exists in DB for this external_id
    stmt = select(func.count(WeatherReport.id)).where(WeatherReport.external_id == unique_ext_id)
    res = await db_session.execute(stmt)
    count = res.scalar()
    assert count == 1

    # Cleanup
    await db_session.execute(
        delete(RealtimeOutbox).where(RealtimeOutbox.entity_id == str(report1_id))
    )
    await db_session.execute(delete(WeatherReport).where(WeatherReport.id == report1_id))
    await db_session.commit()


async def test_observation_worker_persistence(db_session: AsyncSession) -> None:
    """Proves ObservationWorker consumes observations and persists to weather_observations."""
    mock_redis, streams = _create_mock_stream_bus()
    mock_stream_svc = StreamService(client=mock_redis)

    unique_ext_id = f"OBS-TEST-{uuid.uuid4().hex[:6]}"
    now = datetime.now(timezone.utc)
    obs_event = NormalizedObservationEvent(
        source_code="TEST_CWC",
        external_id=unique_ext_id,
        station_code="CWC-TEST-STA",
        station_name="Test River Basin Gauge",
        latitude=17.3850,
        longitude=78.4867,
        observed_at=now,
        water_level_m=62.4,
        raw_metrics={"basin": "Musi"},
    )

    await mock_stream_svc.publish_observation(obs_event)
    assert len(streams["stream:weather:observations"]) == 1

    @asynccontextmanager
    async def session_factory() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    obs_svc = ObservationService()
    worker = ObservationWorker(
        stream_svc=mock_stream_svc,
        obs_svc=obs_svc,
        session_factory=session_factory,  # type: ignore[arg-type]
    )

    results = await worker.process_batch(count=10)
    assert len(results) == 1
    _, observation = results[0]
    assert observation is not None
    assert observation.station_code == "CWC-TEST-STA"
    assert observation.water_level_m == 62.4

    # Verify query in PostgreSQL
    stmt = select(WeatherObservation).where(WeatherObservation.external_id == unique_ext_id)
    res = await db_session.execute(stmt)
    persisted = res.scalar_one_or_none()
    assert persisted is not None
    assert persisted.station_name == "Test River Basin Gauge"

    # Cleanup
    await db_session.execute(
        delete(WeatherObservation).where(WeatherObservation.external_id == unique_ext_id)
    )
    await db_session.commit()


async def test_evidence_worker_persistence(db_session: AsyncSession) -> None:
    """Proves EvidenceWorker consumes evidence and persists to evidence_media."""
    mock_redis, streams = _create_mock_stream_bus()
    mock_stream_svc = StreamService(client=mock_redis)

    unique_ext_id = f"EV-TEST-{uuid.uuid4().hex[:6]}"
    now = datetime.now(timezone.utc)
    ev_event = NormalizedEvidenceEvent(
        source_code="TEST_GDELT",
        external_id=unique_ext_id,
        evidence_type="NEWS_ARTICLE",
        title="Heavy rains trigger waterlogging across low-lying areas",
        url=f"https://news.example.com/article-{unique_ext_id}",
        publisher_domain="news.example.com",
        published_at=now,
        text_snippet="Civic authorities issue localized advisories.",
    )

    await mock_stream_svc.publish_evidence(ev_event)
    assert len(streams["stream:weather:evidence"]) == 1

    @asynccontextmanager
    async def session_factory() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    ev_svc = EvidenceService()
    worker = EvidenceWorker(
        stream_svc=mock_stream_svc,
        ev_svc=ev_svc,
        session_factory=session_factory,  # type: ignore[arg-type]
    )

    results = await worker.process_batch(count=10)
    assert len(results) == 1
    _, evidence = results[0]
    assert evidence is not None
    assert evidence.evidence_type == "NEWS_ARTICLE"

    # Verify query in PostgreSQL
    stmt = select(EvidenceItem).where(EvidenceItem.external_id == unique_ext_id)
    res = await db_session.execute(stmt)
    persisted = res.scalar_one_or_none()
    assert persisted is not None
    assert persisted.publisher_domain == "news.example.com"

    # Cleanup
    await db_session.execute(delete(EvidenceItem).where(EvidenceItem.external_id == unique_ext_id))
    await db_session.commit()


async def test_e2e_external_event_to_intelligence_pipeline(db_session: AsyncSession) -> None:
    """End-to-End integration proof for external event ingestion through to intelligence."""
    mock_redis, streams = _create_mock_stream_bus()
    mock_realtime = RealtimeService(client=mock_redis)
    mock_stream_svc = StreamService(client=mock_redis)
    report_svc = ReportService(realtime_svc=mock_realtime)

    # 1. External adapter event published
    unique_ext_id = f"EXT-NDMA-{uuid.uuid4().hex[:6]}"
    now = datetime.now(timezone.utc)
    event = NormalizedIngestionEvent(
        source_code="NDMA_SACHET",
        external_id=unique_ext_id,
        category_code="CYCLONE_HIGH_WIND",
        severity="SEVERE",
        title="Cyclone Warning: Coastal Gale Warning",
        description="Gale force wind speed 70-80 kmph gusting to 90 kmph.",
        location_name="Ratnagiri, Maharashtra",
        latitude=16.9902,
        longitude=73.3120,
        occurred_at=now,
    )
    await mock_stream_svc.publish_event(event)

    @asynccontextmanager
    async def session_factory() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    # 2. IngestionWorker consumes event and persists report in QUEUED state + stages outbox
    ingestion_w = IngestionWorker(
        stream_svc=mock_stream_svc,
        report_svc=report_svc,
        session_factory=session_factory,  # type: ignore[arg-type]
    )
    batch_results = await ingestion_w.process_batch(count=10)
    assert len(batch_results) == 1
    _, report = batch_results[0]
    assert report is not None
    assert report.processing_status == "QUEUED"
    report_id = report.id

    # 3. OutboxWorker relays staged orchestration event to stream:weather:orchestration
    outbox_w = RealtimeOutboxWorker(client=mock_redis)
    await outbox_w.publish_pending_batch(db_session)

    orch_messages = streams["stream:weather:orchestration"]
    assert len(orch_messages) >= 1
    target_msg = next(
        f
        for _, f in orch_messages
        if f.get("event_type") == OrchestrationEventType.INCIDENT_INGESTED.value
        and f.get("aggregate_id") == str(report_id)
    )
    assert target_msg is not None

    # 4. OrchestrationDispatcher reads from stream and executes REAL IncidentPipeline
    dispatcher = OrchestrationDispatcher(client=mock_redis)
    if "data" in target_msg:
        data_dict = (
            json.loads(target_msg["data"])
            if isinstance(target_msg["data"], str)
            else target_msg["data"]
        )
        orch_event = OrchestrationEvent.model_validate(data_dict)
    else:
        orch_event = OrchestrationEvent.model_validate(target_msg)

    # Execute dispatcher routing with zero pipeline mocks
    dispatch_res = await dispatcher.process_event(db=db_session, event=orch_event)
    assert dispatch_res.outcome is not None

    # 5. Verify WeatherReport in PostgreSQL transitioned to COMPLETED with credibility score
    await db_session.commit()
    stmt = select(WeatherReport).where(WeatherReport.id == report_id)
    res = await db_session.execute(stmt)
    persisted_report = res.scalar_one()

    assert persisted_report.processing_status == "COMPLETED"
    assert persisted_report.credibility_score > 0.0
    assert persisted_report.credibility_explanation is not None
    assert persisted_report.raw_payload is not None
    assert (
        persisted_report.raw_payload.get("orchestration", {}).get("overall_readiness")
        == OverallReadiness.INTELLIGENCE_READY.value
    )

    # 6. Clean up test record
    await db_session.execute(
        delete(RealtimeOutbox).where(RealtimeOutbox.entity_id == str(report_id))
    )
    await db_session.execute(delete(WeatherReport).where(WeatherReport.id == report_id))
    await db_session.commit()
