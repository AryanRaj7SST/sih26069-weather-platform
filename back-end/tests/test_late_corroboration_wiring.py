"""Comprehensive tests for late evidence & observation reactive corroboration wiring.

Verifies:
1. EvidenceWorker & ObservationWorker atomic outbox staging in the SAME transaction.
2. End-to-end reactive re-triggering from outbox to credibility recomputation.
3. Idempotent duplicate event handling.
4. Preservation of human overrides and operator verification status.
5. No-match clean acknowledgment.
6. Redis unavailability resilience (outbox remains PENDING, zero trigger loss).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.schemas import (
    NormalizedEvidenceEvent,
    NormalizedObservationEvent,
)
from app.models.category import EventCategory
from app.models.corroboration import IncidentObservationCorroboration
from app.models.evidence import EvidenceItem, IncidentEvidenceLink
from app.models.outbox import RealtimeOutbox
from app.models.report import WeatherReport
from app.models.source import Source
from app.orchestration.dispatcher import OrchestrationDispatcher
from app.orchestration.events import (
    AggregateType,
    OrchestrationEvent,
    OrchestrationEventType,
    StageName,
    StageOutcome,
)
from app.services.evidence_service import EvidenceService
from app.services.observation_service import ObservationService
from app.services.realtime_service import RealtimeService


async def get_or_create_flood_category(session: AsyncSession) -> EventCategory:
    """Helper to fetch canonical FLOOD_WATERLOGGING category or create if missing."""
    stmt = select(EventCategory).where(EventCategory.category_code == "FLOOD_WATERLOGGING")
    res = await session.execute(stmt)
    cat = res.scalar_one_or_none()
    if not cat:
        cat = EventCategory(
            category_code="FLOOD_WATERLOGGING",
            title="Flood & Waterlogging",
            severity_default="HIGH",
            color_hex="#3B82F6",
            icon_name="flood",
        )
        session.add(cat)
        await session.flush()
    return cat


@pytest.mark.asyncio
async def test_evidence_service_stages_orchestration_outbox_atomically(
    db_session: AsyncSession,
) -> None:
    """Test 1: Evidence ingestion stages outbox event in the same transaction."""
    uid = uuid.uuid4().hex[:8]
    event = NormalizedEvidenceEvent(
        source_code=f"EVI_TEST_{uid}",
        external_id=f"ext_evi_{uid}",
        evidence_type="NEWS_ARTICLE",
        title=f"Severe Flooding in Coastal Puri {uid}",
        url=f"https://news.example.com/flood-{uid}",
        publisher_domain="news.example.com",
        language="en",
        published_at=datetime.now(timezone.utc),
        text_snippet="Major waterlogging across key transit roads in Puri.",
    )

    ev_svc = EvidenceService()
    evidence = await ev_svc.ingest_normalized_evidence(session=db_session, event=event)
    assert evidence.id is not None

    # Verify outbox row staged atomically with matching event_type and aggregate_id
    stmt = select(RealtimeOutbox).where(
        RealtimeOutbox.entity_id == str(evidence.id),
        RealtimeOutbox.event_type == "orchestration.evidence_link_modified",
    )
    res = await db_session.execute(stmt)
    outbox_row = res.scalar_one_or_none()
    assert outbox_row is not None
    assert outbox_row.status in ("PENDING", "PUBLISHED")
    assert outbox_row.payload["event_type"] == OrchestrationEventType.EVIDENCE_LINK_MODIFIED.value
    assert outbox_row.payload["aggregate_type"] == AggregateType.EVIDENCE_ITEM.value
    assert outbox_row.payload["aggregate_id"] == str(evidence.id)

    # Clean outbox state
    outbox_row.status = "PUBLISHED"
    await db_session.commit()


@pytest.mark.asyncio
async def test_observation_service_stages_orchestration_outbox_atomically(
    db_session: AsyncSession,
) -> None:
    """Test 2: Observation ingestion stages outbox event in the same transaction."""
    uid = uuid.uuid4().hex[:8]
    event = NormalizedObservationEvent(
        source_code=f"OBS_TEST_{uid}",
        external_id=f"ext_obs_{uid}",
        station_code=f"AWS_{uid}",
        station_name=f"Puri AWS {uid}",
        latitude=19.8135,
        longitude=85.8312,
        observed_at=datetime.now(timezone.utc),
        rainfall_mm=65.4,
        temperature_c=27.5,
    )

    obs_svc = ObservationService()
    obs = await obs_svc.ingest_normalized_observation(session=db_session, event=event)
    assert obs.id is not None

    # Verify outbox row staged atomically
    stmt = select(RealtimeOutbox).where(
        RealtimeOutbox.entity_id == str(obs.id),
        RealtimeOutbox.event_type == "orchestration.observation_corroboration_modified",
    )
    res = await db_session.execute(stmt)
    outbox_row = res.scalar_one_or_none()
    assert outbox_row is not None
    assert outbox_row.status in ("PENDING", "PUBLISHED")
    assert (
        outbox_row.payload["event_type"]
        == OrchestrationEventType.OBSERVATION_CORROBORATION_MODIFIED.value
    )
    assert outbox_row.payload["aggregate_type"] == AggregateType.WEATHER_OBSERVATION.value
    assert outbox_row.payload["aggregate_id"] == str(obs.id)

    # Clean outbox state
    outbox_row.status = "PUBLISHED"
    await db_session.commit()


@pytest.mark.asyncio
async def test_completed_report_late_matching_evidence_triggers_credibility_recalc(
    db_session: AsyncSession,
) -> None:
    """Test 3: Late matching evidence triggers evidence link and credibility recalculation."""
    uid = uuid.uuid4().hex[:8]

    cat = await get_or_create_flood_category(db_session)
    source = Source(
        source_code=f"SRC_{uid}",
        name="Citizen App",
        source_type="CITIZEN_REPORT",
        base_trust_score=0.60,
        is_active=True,
    )
    db_session.add(source)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    # Create already COMPLETED report with baseline credibility
    report = WeatherReport(
        tracking_id=f"RPT-EVI-{uid}",
        source_id=source.id,
        category_id=cat.id,
        title="Severe Waterlogging in Puri Market",
        description="Streets flooded waist deep around grand road Puri.",
        location_name="Puri, Odisha",
        reported_category=cat.category_code,
        latitude=19.8135,
        longitude=85.8312,
        occurred_at=now,
        geom="SRID=4326;POINT(85.8312 19.8135)",
        processing_status="COMPLETED",
        verification_status="PENDING",
        credibility_score=0.6000,
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    initial_score = report.credibility_score

    # Ingest late matching evidence
    evi_event = NormalizedEvidenceEvent(
        source_code=f"GDELT_{uid}",
        external_id=f"gdel_{uid}",
        evidence_type="NEWS_ARTICLE",
        title="Flash Flood Submerges Grand Road Puri",
        url=f"https://odishareport.com/flood-{uid}",
        publisher_domain="odishareport.com",
        language="en",
        published_at=now,
        text_snippet="Extreme waterlogging reported in Puri Grand Road market.",
    )

    ev_svc = EvidenceService()
    evidence = await ev_svc.ingest_normalized_evidence(session=db_session, event=evi_event)

    # Route event via real dispatcher (no mocking of triggers)
    dispatcher = OrchestrationDispatcher()
    orch_event = OrchestrationEvent(
        event_id=uuid.uuid4(),
        event_type=OrchestrationEventType.EVIDENCE_LINK_MODIFIED,
        aggregate_type=AggregateType.EVIDENCE_ITEM,
        aggregate_id=evidence.id,
        producer="evidence_worker",
        correlation_id=str(evidence.id),
        idempotency_key=f"evidence-link-{evidence.id}",
    )

    res = await dispatcher.process_event(db=db_session, event=orch_event)
    assert res.outcome == StageOutcome.SUCCESS_WITH_RESULTS
    assert report.id in res.affected_incident_ids

    # Verify link created in DB
    link_stmt = select(IncidentEvidenceLink).where(
        IncidentEvidenceLink.report_id == report.id,
        IncidentEvidenceLink.evidence_id == evidence.id,
    )
    link_res = await db_session.execute(link_stmt)
    link = link_res.scalar_one_or_none()
    assert link is not None
    assert link.confidence_score > 0.0

    # Verify report credibility lifted above initial baseline
    await db_session.refresh(report)
    assert report.credibility_score > initial_score


@pytest.mark.asyncio
async def test_completed_report_late_matching_observation_triggers_credibility_recalc(
    db_session: AsyncSession,
) -> None:
    """Test 4: Late matching sensor observation triggers observation corroboration recalculation."""
    uid = uuid.uuid4().hex[:8]

    cat = await get_or_create_flood_category(db_session)
    source = Source(
        source_code=f"SRC_OBS_{uid}",
        name="Citizen App",
        source_type="CITIZEN_REPORT",
        base_trust_score=0.55,
        is_active=True,
    )
    db_session.add(source)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    report = WeatherReport(
        tracking_id=f"RPT-OBS-{uid}",
        source_id=source.id,
        category_id=cat.id,
        title="Severe River Flood in Anuppur",
        description="Narmada river water level rising rapidly entering town.",
        location_name="Anuppur, Madhya Pradesh",
        reported_category="FLOOD_WATERLOGGING",
        latitude=23.4567,
        longitude=81.2345,
        occurred_at=now,
        geom="SRID=4326;POINT(81.2345 23.4567)",
        processing_status="COMPLETED",
        verification_status="PENDING",
        credibility_score=0.5500,
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)

    initial_score = report.credibility_score

    # Ingest late matching hydrological observation within 500m and same timestamp
    obs_event = NormalizedObservationEvent(
        source_code=f"CWC_NWDP_{uid}",
        external_id=f"cwc_{uid}",
        station_code=f"ANUPPUR_CWC_{uid}",
        station_name="Anuppur CWC Telemetry",
        latitude=23.4570,
        longitude=81.2348,
        observed_at=now,
        water_level_m=12.5,
        rainfall_mm=78.2,
        temperature_c=26.0,
    )

    obs_svc = ObservationService()
    obs = await obs_svc.ingest_normalized_observation(session=db_session, event=obs_event)

    # Route event via real dispatcher
    dispatcher = OrchestrationDispatcher()
    orch_event = OrchestrationEvent(
        event_id=uuid.uuid4(),
        event_type=OrchestrationEventType.OBSERVATION_CORROBORATION_MODIFIED,
        aggregate_type=AggregateType.WEATHER_OBSERVATION,
        aggregate_id=obs.id,
        producer="observation_worker",
        correlation_id=str(obs.id),
        idempotency_key=f"observation-corr-{obs.id}",
    )

    res = await dispatcher.process_event(db=db_session, event=orch_event)
    assert res.outcome == StageOutcome.SUCCESS_WITH_RESULTS
    assert report.id in res.affected_incident_ids

    # Verify corroboration record created in DB
    corr_stmt = select(IncidentObservationCorroboration).where(
        IncidentObservationCorroboration.report_id == report.id,
        IncidentObservationCorroboration.observation_id == obs.id,
    )
    corr_res = await db_session.execute(corr_stmt)
    corr = corr_res.scalar_one_or_none()
    assert corr is not None
    assert corr.corroboration_score > 0.0

    # Verify report credibility increased
    await db_session.refresh(report)
    assert report.credibility_score > initial_score


@pytest.mark.asyncio
async def test_duplicate_evidence_orchestration_delivery_idempotent(
    db_session: AsyncSession,
) -> None:
    """Test 5: Duplicate evidence delivery does not duplicate links or mutate credibility."""
    uid = uuid.uuid4().hex[:8]

    source = Source(
        source_code=f"SRC_DUP_EVI_{uid}",
        name="Source",
        source_type="CITIZEN_REPORT",
        base_trust_score=0.60,
        is_active=True,
    )
    db_session.add(source)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    report = WeatherReport(
        tracking_id=f"RPT-DUP-EVI-{uid}",
        source_id=source.id,
        title="Cyclone Gale Damage",
        description="High winds destroying tin roofs in Cuttack.",
        location_name="Cuttack, Odisha",
        latitude=20.4625,
        longitude=85.8828,
        occurred_at=now,
        geom="SRID=4326;POINT(85.8828 20.4625)",
        processing_status="COMPLETED",
        verification_status="PENDING",
        credibility_score=0.6000,
    )
    db_session.add(report)
    await db_session.commit()

    evi = EvidenceItem(
        source_id=source.id,
        external_id=f"evi_dup_{uid}",
        evidence_type="NEWS_ARTICLE",
        title="Cyclone Gale Destroys Roofs in Cuttack",
        text_snippet="Widespread wind damage in Cuttack city center.",
        publisher_domain="odishanews.com",
        published_at=now,
    )
    db_session.add(evi)
    await db_session.commit()

    dispatcher = OrchestrationDispatcher()
    orch_event = OrchestrationEvent(
        event_id=uuid.uuid4(),
        event_type=OrchestrationEventType.EVIDENCE_LINK_MODIFIED,
        aggregate_type=AggregateType.EVIDENCE_ITEM,
        aggregate_id=evi.id,
        producer="evidence_worker",
        correlation_id=str(evi.id),
        idempotency_key=f"evidence-link-{evi.id}",
    )

    # First delivery
    res1 = await dispatcher.process_event(db=db_session, event=orch_event)
    assert res1.outcome == StageOutcome.SUCCESS_WITH_RESULTS
    await db_session.refresh(report)
    score_after_first = report.credibility_score

    # Second (duplicate) delivery
    res2 = await dispatcher.process_event(db=db_session, event=orch_event)
    assert res2.outcome == StageOutcome.SUCCESS_WITH_RESULTS
    await db_session.refresh(report)
    score_after_second = report.credibility_score

    assert score_after_second == score_after_first

    # Verify exactly ONE link exists for this (report, evidence) pair
    stmt = select(IncidentEvidenceLink).where(
        IncidentEvidenceLink.report_id == report.id,
        IncidentEvidenceLink.evidence_id == evi.id,
    )
    links = list((await db_session.execute(stmt)).scalars().all())
    assert len(links) == 1


@pytest.mark.asyncio
async def test_duplicate_observation_orchestration_delivery_idempotent(
    db_session: AsyncSession,
) -> None:
    """Test 6: Duplicate observation delivery does not create duplicate corroborations."""
    uid = uuid.uuid4().hex[:8]

    source = Source(
        source_code=f"SRC_DUP_OBS_{uid}",
        name="Source",
        source_type="CITIZEN_REPORT",
        base_trust_score=0.60,
        is_active=True,
    )
    db_session.add(source)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    report = WeatherReport(
        tracking_id=f"RPT-DUP-OBS-{uid}",
        source_id=source.id,
        title="Heavy Rain in Thane",
        description="Inundation near Thane railway station.",
        location_name="Thane, Maharashtra",
        latitude=19.2183,
        longitude=72.9781,
        occurred_at=now,
        geom="SRID=4326;POINT(72.9781 19.2183)",
        processing_status="COMPLETED",
        verification_status="PENDING",
        credibility_score=0.6000,
    )
    db_session.add(report)
    await db_session.commit()

    obs_event = NormalizedObservationEvent(
        source_code=f"IMD_AWS_{uid}",
        external_id=f"obs_dup_{uid}",
        station_code=f"THANE_AWS_{uid}",
        station_name="Thane AWS Station",
        latitude=19.2183,
        longitude=72.9781,
        observed_at=now,
        rainfall_mm=55.0,
    )

    obs_svc = ObservationService()
    obs = await obs_svc.ingest_normalized_observation(session=db_session, event=obs_event)

    dispatcher = OrchestrationDispatcher()
    orch_event = OrchestrationEvent(
        event_id=uuid.uuid4(),
        event_type=OrchestrationEventType.OBSERVATION_CORROBORATION_MODIFIED,
        aggregate_type=AggregateType.WEATHER_OBSERVATION,
        aggregate_id=obs.id,
        producer="observation_worker",
        correlation_id=str(obs.id),
        idempotency_key=f"observation-corr-{obs.id}",
    )

    # First delivery
    await dispatcher.process_event(db=db_session, event=orch_event)
    await db_session.refresh(report)
    score1 = report.credibility_score

    # Duplicate delivery
    await dispatcher.process_event(db=db_session, event=orch_event)
    await db_session.refresh(report)
    score2 = report.credibility_score

    assert score1 == score2

    # Exactly ONE corroboration row exists
    stmt = select(IncidentObservationCorroboration).where(
        IncidentObservationCorroboration.report_id == report.id,
        IncidentObservationCorroboration.observation_id == obs.id,
    )
    corrs = list((await db_session.execute(stmt)).scalars().all())
    assert len(corrs) == 1


@pytest.mark.asyncio
async def test_late_corroboration_preserves_human_overrides_and_verification_status(
    db_session: AsyncSession,
) -> None:
    """Test 7: Late re-trigger preserves operator overrides and verification status."""
    uid = uuid.uuid4().hex[:8]

    source = Source(
        source_code=f"SRC_OVR_{uid}",
        name="Source",
        source_type="CITIZEN_REPORT",
        base_trust_score=0.50,
        is_active=True,
    )
    db_session.add(source)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    # Operator manually marked report VERIFIED
    report = WeatherReport(
        tracking_id=f"RPT-OVR-{uid}",
        source_id=source.id,
        title="Urban Flood",
        description="Severe flooding in residential colony.",
        location_name="Puri, Odisha",
        latitude=19.8135,
        longitude=85.8312,
        occurred_at=now,
        geom="SRID=4326;POINT(85.8312 19.8135)",
        processing_status="COMPLETED",
        verification_status="VERIFIED",  # Operator manual status
        credibility_score=0.5000,
    )
    db_session.add(report)
    await db_session.commit()

    # Pre-existing evidence link with human override
    evi = EvidenceItem(
        source_id=source.id,
        external_id=f"evi_ovr_{uid}",
        evidence_type="NEWS_ARTICLE",
        title="Puri Flood News Article",
        text_snippet="Flood waters enter homes in Puri.",
        publisher_domain="news.com",
        published_at=now,
    )
    db_session.add(evi)
    await db_session.flush()

    human_link = IncidentEvidenceLink(
        report_id=report.id,
        evidence_id=evi.id,
        link_role="IRRELEVANT",
        confidence_score=0.10,
        match_explanation={
            "is_human_override": True,
            "decision": "REJECTED_BY_OPERATOR",
        },
    )
    db_session.add(human_link)
    await db_session.commit()

    # Late re-trigger on this evidence
    dispatcher = OrchestrationDispatcher()
    orch_event = OrchestrationEvent(
        event_id=uuid.uuid4(),
        event_type=OrchestrationEventType.EVIDENCE_LINK_MODIFIED,
        aggregate_type=AggregateType.EVIDENCE_ITEM,
        aggregate_id=evi.id,
        producer="evidence_worker",
        correlation_id=str(evi.id),
        idempotency_key=f"evidence-link-{evi.id}",
    )

    await dispatcher.process_event(db=db_session, event=orch_event)

    # Verify link's human override was preserved
    await db_session.refresh(human_link)
    assert human_link.match_explanation is not None
    assert human_link.match_explanation.get("is_human_override") is True
    assert human_link.link_role == "IRRELEVANT"
    assert human_link.confidence_score == 0.10

    # Verify report's verification_status is still VERIFIED
    await db_session.refresh(report)
    assert report.verification_status == "VERIFIED"


@pytest.mark.asyncio
async def test_no_matching_incidents_clean_acknowledgment(
    db_session: AsyncSession,
) -> None:
    """Test 8: Unmatched evidence produces zero incident writes and clean acknowledgment."""
    uid = uuid.uuid4().hex[:8]

    source = Source(
        source_code=f"SRC_NOMATCH_{uid}",
        name="Source",
        source_type="RSS",
        base_trust_score=0.70,
        is_active=True,
    )
    db_session.add(source)
    await db_session.flush()

    # Evidence in past year 2020 (no active candidate reports)
    historical_time = datetime(2020, 1, 1, 12, 0, tzinfo=timezone.utc)
    evi = EvidenceItem(
        source_id=source.id,
        external_id=f"evi_ladakh_{uid}",
        evidence_type="NEWS_ARTICLE",
        title="Historical High Altitude Snowfall in Leh Ladakh 2020",
        text_snippet="Fresh snowfall blocks mountain passes near Leh.",
        publisher_domain="himalayannews.com",
        published_at=historical_time,
    )
    db_session.add(evi)
    await db_session.commit()

    dispatcher = OrchestrationDispatcher()
    orch_event = OrchestrationEvent(
        event_id=uuid.uuid4(),
        event_type=OrchestrationEventType.EVIDENCE_LINK_MODIFIED,
        aggregate_type=AggregateType.EVIDENCE_ITEM,
        aggregate_id=evi.id,
        producer="evidence_worker",
        correlation_id=str(evi.id),
        idempotency_key=f"evidence-link-{evi.id}",
    )

    res = await dispatcher.process_event(db=db_session, event=orch_event)
    assert res.outcome == StageOutcome.SUCCESS_WITH_RESULTS
    assert res.stage_name == StageName.EVIDENCE
    assert res.affected_incident_ids == []


@pytest.mark.asyncio
async def test_redis_unavailable_outbox_remains_pending_no_trigger_loss(
    db_session: AsyncSession,
) -> None:
    """Test 9: When Redis fails, outbox row remains PENDING without trigger loss."""
    uid = uuid.uuid4().hex[:8]

    # Mock Redis client that fails on XADD
    mock_redis = AsyncMock()
    mock_redis.xadd.side_effect = ConnectionError("Redis connection refused")

    realtime_svc = RealtimeService(client=mock_redis)
    ev_svc = EvidenceService(realtime_svc=realtime_svc)

    event = NormalizedEvidenceEvent(
        source_code=f"EVI_FAIL_{uid}",
        external_id=f"ext_fail_{uid}",
        evidence_type="NEWS_ARTICLE",
        title=f"Storm in Goa {uid}",
        publisher_domain="goanews.com",
        language="en",
        published_at=datetime.now(timezone.utc),
        text_snippet="Heavy rains in Panaji.",
    )

    evidence = await ev_svc.ingest_normalized_evidence(session=db_session, event=event)
    assert evidence.id is not None

    # Verify that the outbox row remains PENDING in PostgreSQL for background outbox worker pickup
    stmt = select(RealtimeOutbox).where(
        RealtimeOutbox.entity_id == str(evidence.id),
        RealtimeOutbox.event_type == "orchestration.evidence_link_modified",
    )
    res = await db_session.execute(stmt)
    outbox_row = res.scalar_one_or_none()
    assert outbox_row is not None
    assert outbox_row.status == "PENDING"
    assert outbox_row.published_at is None

    # Clean outbox state
    outbox_row.status = "PUBLISHED"
    await db_session.commit()
