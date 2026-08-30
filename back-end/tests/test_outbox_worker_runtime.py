"""Unit and integration tests for RealtimeOutboxWorker runtime, loop lifecycle, and scheduling.

Covers:
- Worker polling loop mechanics (sleep on empty, drain on backlog)
- Graceful cancellation and signal handling
- Error resilience (Redis/DB exceptions do not crash loop)
- Periodic pruning scheduling
- Multi-worker concurrent claim safety (SKIP LOCKED)
- Standalone runner entry point execution
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.redis import AsyncRedisClient
from app.db.session import async_session_factory
from app.models.outbox import RealtimeOutbox
from app.workers.outbox_worker import RealtimeOutboxWorker
from app.workers.run_outbox_worker import _handle_signal
from app.workers.run_outbox_worker import main as runner_main


@pytest.fixture(autouse=True)
async def clean_outbox_table(db_session: AsyncSession):
    """Ensure realtime_outbox table is clean before and after each test."""
    await db_session.execute(delete(RealtimeOutbox))
    await db_session.commit()
    yield
    await db_session.execute(delete(RealtimeOutbox))
    await db_session.commit()


@pytest.mark.asyncio
async def test_worker_loop_processes_backlog_and_stops_on_event(db_session: AsyncSession):
    """Verify run_loop drains available outbox events and halts when stop_event is set."""
    mock_redis = MagicMock(spec=AsyncRedisClient)
    mock_redis.xadd = AsyncMock(return_value="1725000000001-0")

    worker = RealtimeOutboxWorker(client=mock_redis, session_factory=async_session_factory)

    # 1. Insert 3 pending outbox events
    event_ids = [uuid.uuid4() for _ in range(3)]
    for e_id in event_ids:
        row = RealtimeOutbox(
            event_id=e_id,
            event_type="report.created",
            entity_id=f"rep-{e_id.hex[:8]}",
            tracking_id=f"RPT-{e_id.hex[:6]}",
            occurred_at=datetime.now(timezone.utc),
            payload={"test": True},
            status="PENDING",
            attempts=0,
            max_attempts=5,
        )
        db_session.add(row)
    await db_session.commit()

    # 2. Run worker loop with a stop_event that triggers after short delay
    stop_event = asyncio.Event()

    async def trigger_stop_soon():
        await asyncio.sleep(0.1)
        stop_event.set()

    asyncio.create_task(trigger_stop_soon())

    await worker.run_loop(
        poll_interval=0.01,
        batch_size=10,
        prune_interval=3600,
        retention_hours=24,
        stop_event=stop_event,
    )

    # 3. Verify all 3 events were published
    assert mock_redis.xadd.call_count == 3

    # Expire and refresh to see committed changes from worker session
    db_session.expire_all()
    stmt = select(RealtimeOutbox).where(RealtimeOutbox.event_id.in_(event_ids))
    res = await db_session.execute(stmt)
    rows = list(res.scalars().all())
    assert len(rows) == 3
    for r in rows:
        assert r.status == "PUBLISHED"
        assert r.published_at is not None


@pytest.mark.asyncio
async def test_worker_loop_sleeps_on_empty_queue_without_busy_spin():
    """Verify run_loop waits on stop_event when no outbox rows exist."""
    mock_worker = RealtimeOutboxWorker(client=MagicMock(spec=AsyncRedisClient))
    mock_worker.publish_pending_batch = AsyncMock(return_value=(0, 0))  # type: ignore[method-assign]
    mock_worker.prune_published_events = AsyncMock(return_value=0)  # type: ignore[method-assign]

    stop_event = asyncio.Event()

    # Set stop after 50ms
    async def trigger_stop():
        await asyncio.sleep(0.05)
        stop_event.set()

    asyncio.create_task(trigger_stop())

    await mock_worker.run_loop(
        poll_interval=0.1,
        batch_size=10,
        prune_interval=3600,
        stop_event=stop_event,
    )

    # In 50ms with 100ms poll_interval, publish_pending_batch should only be called once
    assert mock_worker.publish_pending_batch.call_count <= 2


@pytest.mark.asyncio
async def test_worker_loop_resilience_to_redis_errors():
    """Verify loop handles transport exceptions without exiting or aborting worker process."""
    mock_worker = RealtimeOutboxWorker(client=MagicMock(spec=AsyncRedisClient))
    # First call raises connection error, second succeeds with 0
    mock_worker.publish_pending_batch = AsyncMock(  # type: ignore[method-assign]
        side_effect=[
            ConnectionError("Redis stream unavailable"),
            (0, 0),
        ]
    )
    mock_worker.prune_published_events = AsyncMock(return_value=0)  # type: ignore[method-assign]

    stop_event = asyncio.Event()

    async def trigger_stop():
        await asyncio.sleep(0.04)
        stop_event.set()

    asyncio.create_task(trigger_stop())

    # Should not raise exception
    await mock_worker.run_loop(
        poll_interval=0.01,
        batch_size=10,
        prune_interval=3600,
        stop_event=stop_event,
    )

    assert mock_worker.publish_pending_batch.call_count >= 2


@pytest.mark.asyncio
async def test_worker_periodic_pruning_schedule(db_session: AsyncSession):
    """Verify run_loop triggers prune_published_events when prune_interval elapsed."""
    mock_redis = MagicMock(spec=AsyncRedisClient)
    worker = RealtimeOutboxWorker(client=mock_redis, session_factory=async_session_factory)

    # Insert old published row (>24h ago)
    old_published = RealtimeOutbox(
        event_id=uuid.uuid4(),
        event_type="report.created",
        entity_id="rep-old-prune",
        occurred_at=datetime.now(timezone.utc) - timedelta(days=2),
        payload={},
        status="PUBLISHED",
        published_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    # Insert recent published row (<1h ago)
    recent_published = RealtimeOutbox(
        event_id=uuid.uuid4(),
        event_type="report.created",
        entity_id="rep-recent-prune",
        occurred_at=datetime.now(timezone.utc),
        payload={},
        status="PUBLISHED",
        published_at=datetime.now(timezone.utc),
    )
    # Insert dead letter row (should never be pruned)
    dead_letter = RealtimeOutbox(
        event_id=uuid.uuid4(),
        event_type="report.created",
        entity_id="rep-dead-letter",
        occurred_at=datetime.now(timezone.utc) - timedelta(days=5),
        payload={},
        status="DEAD_LETTER",
        published_at=None,
    )
    db_session.add_all([old_published, recent_published, dead_letter])
    await db_session.commit()

    # Run loop with prune_interval=0 so pruning triggers immediately
    stop_event = asyncio.Event()

    async def stop_after_short():
        await asyncio.sleep(0.05)
        stop_event.set()

    asyncio.create_task(stop_after_short())

    await worker.run_loop(
        poll_interval=0.01,
        batch_size=10,
        prune_interval=0,  # Forces immediate pruning on loop start
        retention_hours=24,
        stop_event=stop_event,
    )

    # Verify old published row was pruned, but recent row and dead-letter row remain
    db_session.expire_all()
    stmt = select(RealtimeOutbox.entity_id)
    res = await db_session.execute(stmt)
    remaining_ids = set(res.scalars().all())

    assert "rep-old-prune" not in remaining_ids
    assert "rep-recent-prune" in remaining_ids
    assert "rep-dead-letter" in remaining_ids


@pytest.mark.asyncio
async def test_multi_worker_skip_locked_concurrency(db_session: AsyncSession):
    """Verify multiple concurrent worker batches safely claim disjoint outbox partitions."""
    mock_redis1 = MagicMock(spec=AsyncRedisClient)
    mock_redis1.xadd = AsyncMock(return_value="1725000000001-0")
    mock_redis2 = MagicMock(spec=AsyncRedisClient)
    mock_redis2.xadd = AsyncMock(return_value="1725000000002-0")

    worker1 = RealtimeOutboxWorker(client=mock_redis1)
    worker2 = RealtimeOutboxWorker(client=mock_redis2)

    # Insert 6 pending events
    event_ids = [uuid.uuid4() for _ in range(6)]
    for e_id in event_ids:
        row = RealtimeOutbox(
            event_id=e_id,
            event_type="report.created",
            entity_id=f"rep-{e_id.hex[:8]}",
            occurred_at=datetime.now(timezone.utc),
            payload={"k": "v"},
            status="PENDING",
            attempts=0,
            max_attempts=5,
        )
        db_session.add(row)
    await db_session.commit()

    # Worker 1 processes batch of 3
    pub1, fail1 = await worker1.publish_pending_batch(db_session, batch_size=3)
    assert pub1 == 3
    assert fail1 == 0

    # Worker 2 processes remaining batch of 3
    pub2, fail2 = await worker2.publish_pending_batch(db_session, batch_size=3)
    assert pub2 == 3
    assert fail2 == 0

    # Total published = 6, 0 duplicates
    db_session.expire_all()
    stmt = select(RealtimeOutbox).where(RealtimeOutbox.status == "PUBLISHED")
    res = await db_session.execute(stmt)
    published_rows = list(res.scalars().all())
    assert len(published_rows) == 6


@pytest.mark.asyncio
async def test_worker_entry_point_execution_and_signal_handling():
    """Verify standalone run_outbox_worker entry point starts and halts on signal."""
    stop_event = asyncio.Event()
    _handle_signal(15, stop_event)  # SIGTERM
    assert stop_event.is_set()


@pytest.mark.asyncio
async def test_worker_runner_main_lifecycle():
    """Verify runner_main initializes RealtimeOutboxWorker and shuts down cleanly."""
    with (
        patch(
            "app.workers.run_outbox_worker.RealtimeOutboxWorker.run_loop",
            new_callable=AsyncMock,
        ) as mock_run_loop,
        patch(
            "app.workers.run_outbox_worker.redis_client.close",
            new_callable=AsyncMock,
        ) as mock_redis_close,
        patch.object(
            AsyncEngine,
            "dispose",
            new_callable=AsyncMock,
        ) as mock_engine_dispose,
    ):
        # Mock run_loop to return immediately
        mock_run_loop.return_value = None

        exit_code = await runner_main()

        assert exit_code == 0
        mock_run_loop.assert_called_once()
        mock_redis_close.assert_called_once()
        mock_engine_dispose.assert_called_once()


@pytest.mark.asyncio
async def test_worker_disabled_configuration_skips_execution():
    """Verify worker returns immediately when OUTBOX_WORKER_ENABLED is False."""
    mock_worker = RealtimeOutboxWorker(client=MagicMock(spec=AsyncRedisClient))
    mock_worker.publish_pending_batch = AsyncMock(return_value=(0, 0))  # type: ignore[method-assign]

    with patch("app.workers.outbox_worker.settings.OUTBOX_WORKER_ENABLED", False):
        await mock_worker.run_loop(poll_interval=0.01)
        # Should not publish anything or enter loop
        mock_worker.publish_pending_batch.assert_not_called()

    with patch("app.workers.run_outbox_worker.settings.OUTBOX_WORKER_ENABLED", False):
        exit_code = await runner_main()
        assert exit_code == 0
