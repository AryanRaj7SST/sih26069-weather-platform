"""End-to-end integration tests for Realtime Event Pipeline.

Verifies complete flow:
Domain Mutation -> PostgreSQL -> Realtime Outbox -> Redis Stream -> Event Contract
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import AsyncRedisClient
from app.models.outbox import RealtimeOutbox
from app.models.report import WeatherReport
from app.models.verification import VerificationEvent
from app.schemas.report import CitizenReportCreate
from app.services.realtime_service import RealtimeService
from app.services.report_service import InvalidStateTransitionError, ReportService
from app.workers.outbox_worker import RealtimeOutboxWorker


@pytest.fixture(autouse=True)
async def clean_outbox_table(db_session: AsyncSession):
    """Ensure realtime_outbox table is clean before and after each integration test."""
    await db_session.execute(delete(RealtimeOutbox))
    await db_session.commit()
    yield
    await db_session.execute(delete(RealtimeOutbox))
    await db_session.commit()


@pytest.mark.asyncio
async def test_e2e_report_creation_mutation_to_outbox_to_redis_event(
    db_session: AsyncSession,
):
    """Verify citizen report creation commits DB, stages outbox, and publishes to Redis Stream."""
    mock_redis = MagicMock(spec=AsyncRedisClient)
    mock_redis.xadd = AsyncMock(return_value="1725000000001-0")

    mock_realtime = RealtimeService(client=mock_redis)
    report_svc = ReportService(realtime_svc=mock_realtime)

    payload = CitizenReportCreate(
        latitude=19.0760,
        longitude=72.8777,
        category_code="FLOOD_WATERLOGGING",
        severity="HIGH",
        title="E2E Realtime Report Ingestion",
        description="Severe waterlogging near station",
        location_name="Dadar Central",
    )

    report, media_count = await report_svc.create_citizen_report(
        session=db_session,
        payload=payload,
    )

    try:
        assert report is not None
        assert report.id is not None

        # 1. Verify WeatherReport persisted in PostgreSQL
        stmt_rep = select(WeatherReport).where(WeatherReport.id == report.id)
        res_rep = await db_session.execute(stmt_rep)
        persisted_report = res_rep.scalar_one_or_none()
        assert persisted_report is not None
        assert persisted_report.title == "E2E Realtime Report Ingestion"

        # 2. Verify RealtimeOutbox row persisted in PostgreSQL
        stmt_out = select(RealtimeOutbox).where(
            RealtimeOutbox.entity_id == str(report.id),
            RealtimeOutbox.event_type == "report.created",
        )
        res_out = await db_session.execute(stmt_out)
        outbox_row = res_out.scalar_one_or_none()
        assert outbox_row is not None
        assert outbox_row.event_type == "report.created"
        assert outbox_row.status == "PENDING"
        assert outbox_row.tracking_id == report.tracking_id

        # Verify orchestration outbox row also persisted
        stmt_orch = select(RealtimeOutbox).where(
            RealtimeOutbox.entity_id == str(report.id),
            RealtimeOutbox.event_type == "orchestration.incident_ingested",
        )
        res_orch = await db_session.execute(stmt_orch)
        orch_row = res_orch.scalar_one_or_none()
        assert orch_row is not None
        assert orch_row.status == "PENDING"

        # 3. Verify Redis xadd was called for both streams (realtime UI + orchestration)
        assert mock_redis.xadd.call_count == 2
        calls = mock_redis.xadd.call_args_list
        stream_names = {call[0][0] for call in calls}
        assert "stream:weather:realtime" in stream_names
        assert "stream:weather:orchestration" in stream_names

        # 4. Verify OutboxWorker transitions outbox to PUBLISHED
        worker = RealtimeOutboxWorker(client=mock_redis)
        published_count, failed_count = await worker.publish_pending_batch(
            session=db_session, batch_size=10
        )
        assert published_count >= 2
        assert failed_count == 0

        await db_session.refresh(outbox_row)
        assert outbox_row.status == "PUBLISHED"
        assert outbox_row.published_at is not None

        await db_session.refresh(orch_row)
        assert orch_row.status == "PUBLISHED"
        assert orch_row.published_at is not None

    finally:
        # Cleanup
        await db_session.execute(
            delete(RealtimeOutbox).where(RealtimeOutbox.entity_id == str(report.id))
        )
        await db_session.execute(delete(WeatherReport).where(WeatherReport.id == report.id))
        await db_session.commit()


@pytest.mark.asyncio
async def test_e2e_verification_transitions_to_outbox_to_redis_events(
    db_session: AsyncSession,
):
    """Verify verification transitions stage outbox and publish to Redis."""
    mock_redis = MagicMock(spec=AsyncRedisClient)
    mock_redis.xadd = AsyncMock(return_value="1725000000002-0")

    mock_realtime = RealtimeService(client=mock_redis)
    report_svc = ReportService(realtime_svc=mock_realtime)

    # 1. Create a base report
    payload = CitizenReportCreate(
        latitude=19.1136,
        longitude=72.8697,
        category_code="HEAVY_RAINFALL",
        severity="MODERATE",
        title="E2E Transition Base Report",
        description="Rainfall intensifying",
        location_name="Andheri East",
    )
    report, _ = await report_svc.create_citizen_report(
        session=db_session,
        payload=payload,
    )
    mock_redis.xadd.reset_mock()

    try:
        # 2. Transition PENDING -> UNDER_REVIEW
        report_under_review = await report_svc.update_verification_status(
            session=db_session,
            report_id_or_tracking=str(report.id),
            new_status="UNDER_REVIEW",
            notes="Assigned to field team",
        )
        assert report_under_review.verification_status == "UNDER_REVIEW"

        # Verify Outbox and Redis for UNDER_REVIEW
        stmt_out1 = (
            select(RealtimeOutbox)
            .where(
                RealtimeOutbox.entity_id == str(report.id),
                RealtimeOutbox.event_type == "report.verification_changed",
            )
            .order_by(RealtimeOutbox.created_at.desc())
        )
        res_out1 = await db_session.execute(stmt_out1)
        outbox_1 = res_out1.scalars().first()
        assert outbox_1 is not None
        assert outbox_1.payload["previous_status"] == "PENDING"
        assert outbox_1.payload["new_status"] == "UNDER_REVIEW"

        mock_redis.xadd.assert_called_once()
        _, fields1 = mock_redis.xadd.call_args[0]
        assert fields1["event_type"] == "report.verification_changed"
        assert "UNDER_REVIEW" in fields1["payload"]

        mock_redis.xadd.reset_mock()

        # 3. Transition UNDER_REVIEW -> VERIFIED
        report_verified = await report_svc.update_verification_status(
            session=db_session,
            report_id_or_tracking=str(report.id),
            new_status="VERIFIED",
            notes="Field team corroborated",
        )
        assert report_verified.verification_status == "VERIFIED"

        res_out2 = await db_session.execute(stmt_out1)
        outbox_2 = res_out2.scalars().first()
        assert outbox_2 is not None
        assert outbox_2.payload["previous_status"] == "UNDER_REVIEW"
        assert outbox_2.payload["new_status"] == "VERIFIED"

        mock_redis.xadd.assert_called_once()
        _, fields2 = mock_redis.xadd.call_args[0]
        assert "VERIFIED" in fields2["payload"]

    finally:
        # Cleanup
        await db_session.execute(
            delete(VerificationEvent).where(VerificationEvent.report_id == report.id)
        )
        await db_session.execute(
            delete(RealtimeOutbox).where(RealtimeOutbox.entity_id == str(report.id))
        )
        await db_session.execute(delete(WeatherReport).where(WeatherReport.id == report.id))
        await db_session.commit()


@pytest.mark.asyncio
async def test_e2e_invalid_transition_produces_no_outbox_and_no_redis_publish(
    db_session: AsyncSession,
):
    """Verify illegal status transition raises error and produces zero outbox/Redis emissions."""
    mock_redis = MagicMock(spec=AsyncRedisClient)
    mock_redis.xadd = AsyncMock(return_value="1725000000003-0")

    mock_realtime = RealtimeService(client=mock_redis)
    report_svc = ReportService(realtime_svc=mock_realtime)

    # 1. Create and verify a report
    payload = CitizenReportCreate(
        latitude=18.9220,
        longitude=72.8347,
        category_code="CYCLONE_STORM_SURGE",
        severity="SEVERE",
        title="E2E Invalid Transition Report",
        description="High tidal surge",
        location_name="Colaba",
    )
    report, _ = await report_svc.create_citizen_report(
        session=db_session,
        payload=payload,
    )
    await report_svc.update_verification_status(
        session=db_session,
        report_id_or_tracking=str(report.id),
        new_status="UNDER_REVIEW",
    )
    await report_svc.update_verification_status(
        session=db_session,
        report_id_or_tracking=str(report.id),
        new_status="VERIFIED",
    )
    mock_redis.xadd.reset_mock()

    try:
        # Count existing verification events
        stmt_ev_count = select(VerificationEvent).where(VerificationEvent.report_id == report.id)
        res_ev1 = await db_session.execute(stmt_ev_count)
        initial_ev_count = len(res_ev1.scalars().all())

        # 2. Attempt illegal transition: VERIFIED -> REJECTED (terminal state violation)
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            await report_svc.update_verification_status(
                session=db_session,
                report_id_or_tracking=str(report.id),
                new_status="REJECTED",
                notes="Illegal transition attempt",
            )
        assert exc_info.value.current_status == "VERIFIED"
        assert exc_info.value.target_status == "REJECTED"

        # 3. Assert DB state untouched
        res_ev2 = await db_session.execute(stmt_ev_count)
        final_ev_count = len(res_ev2.scalars().all())
        assert final_ev_count == initial_ev_count

        # 4. Assert zero Redis xadd calls
        mock_redis.xadd.assert_not_called()

    finally:
        # Cleanup
        await db_session.execute(
            delete(VerificationEvent).where(VerificationEvent.report_id == report.id)
        )
        await db_session.execute(
            delete(RealtimeOutbox).where(RealtimeOutbox.entity_id == str(report.id))
        )
        await db_session.execute(delete(WeatherReport).where(WeatherReport.id == report.id))
        await db_session.commit()


@pytest.mark.asyncio
async def test_e2e_redis_failure_keeps_outbox_pending_for_worker_recovery(
    db_session: AsyncSession,
):
    """Verify Redis failure during mutation leaves outbox PENDING, recovered by OutboxWorker."""
    mock_failing_redis = MagicMock(spec=AsyncRedisClient)
    mock_failing_redis.xadd = AsyncMock(side_effect=ConnectionError("Redis connection refused"))

    mock_realtime = RealtimeService(client=mock_failing_redis)
    report_svc = ReportService(realtime_svc=mock_realtime)

    payload = CitizenReportCreate(
        latitude=19.0178,
        longitude=72.8478,
        category_code="HEAVY_RAINFALL",
        severity="HIGH",
        title="E2E Redis Outage Report",
        description="Testing recovery when Redis is down",
        location_name="Worli Seaface",
    )

    # 1. Create report while Redis is down
    report, _ = await report_svc.create_citizen_report(
        session=db_session,
        payload=payload,
    )

    try:
        # 2. WeatherReport is successfully committed in DB
        stmt_rep = select(WeatherReport).where(WeatherReport.id == report.id)
        res_rep = await db_session.execute(stmt_rep)
        assert res_rep.scalar_one_or_none() is not None

        # 3. RealtimeOutbox row remains PENDING
        stmt_out = select(RealtimeOutbox).where(
            RealtimeOutbox.entity_id == str(report.id),
            RealtimeOutbox.event_type == "report.created",
        )
        res_out = await db_session.execute(stmt_out)
        outbox_row = res_out.scalar_one_or_none()
        assert outbox_row is not None
        assert outbox_row.status == "PENDING"
        assert outbox_row.published_at is None

        # 4. Simulate Redis recovery and OutboxWorker batch processing
        mock_recovered_redis = MagicMock(spec=AsyncRedisClient)
        mock_recovered_redis.xadd = AsyncMock(return_value="1725000000004-0")

        worker = RealtimeOutboxWorker(client=mock_recovered_redis)
        published_count, failed_count = await worker.publish_pending_batch(
            session=db_session,
            batch_size=10,
        )
        assert published_count >= 2
        assert failed_count == 0

        # 5. Outbox row is now PUBLISHED
        await db_session.refresh(outbox_row)
        assert outbox_row.status == "PUBLISHED"
        assert outbox_row.published_at is not None
        assert mock_recovered_redis.xadd.call_count >= 2

    finally:
        # Cleanup
        await db_session.execute(
            delete(RealtimeOutbox).where(RealtimeOutbox.entity_id == str(report.id))
        )
        await db_session.execute(delete(WeatherReport).where(WeatherReport.id == report.id))
        await db_session.commit()
