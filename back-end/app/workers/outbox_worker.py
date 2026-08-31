"""Outbox worker and publisher for reliable real-time event delivery.

Consumes pending events from the PostgreSQL `realtime_outbox` table using
concurrency-safe row locking (`SKIP LOCKED`) and delivers them to Redis Streams.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.redis import AsyncRedisClient, redis_client
from app.db.session import async_session_factory
from app.models.outbox import RealtimeOutbox

logger = logging.getLogger(__name__)


class RealtimeOutboxWorker:
    """Consumes and publishes pending outbox events to Redis Streams with at-least-once safety."""

    def __init__(
        self,
        client: Optional[AsyncRedisClient] = None,
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
        stream_name: Optional[str] = None,
        maxlen: Optional[int] = None,
    ) -> None:
        self.client = client or redis_client
        self.session_factory = session_factory or async_session_factory
        self.stream_name = stream_name or settings.REALTIME_STREAM_NAME
        self.maxlen = maxlen or settings.REALTIME_STREAM_MAXLEN

    async def publish_pending_batch(
        self,
        session: AsyncSession,
        batch_size: int = 50,
    ) -> Tuple[int, int]:
        """Fetch a batch of pending outbox rows using SKIP LOCKED, publish, and update status.

        Returns (published_count, failed_count).
        """
        now = datetime.now(timezone.utc)
        stmt = (
            select(RealtimeOutbox)
            .where(
                RealtimeOutbox.status == "PENDING",
                or_(
                    RealtimeOutbox.next_retry_at.is_(None),
                    RealtimeOutbox.next_retry_at <= now,
                ),
            )
            .order_by(RealtimeOutbox.created_at.asc())
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )

        res = await session.execute(stmt)
        pending_rows = list(res.scalars().all())

        if not pending_rows:
            return 0, 0

        published_count = 0
        failed_count = 0

        for row in pending_rows:
            if row.event_type.startswith("orchestration."):
                target_stream = "stream:weather:orchestration"
                orch_dict = row.payload
                payload_fields = {
                    "event_id": str(orch_dict.get("event_id", row.event_id)),
                    "event_type": orch_dict.get("event_type", row.event_type),
                    "aggregate_type": orch_dict.get("aggregate_type", ""),
                    "aggregate_id": orch_dict.get("aggregate_id", row.entity_id),
                    "correlation_id": orch_dict.get("correlation_id", ""),
                    "attempt": str(orch_dict.get("attempt", row.attempts + 1)),
                    "data": json.dumps(orch_dict),
                }
            else:
                target_stream = self.stream_name
                payload_fields = {
                    "event_id": str(row.event_id),
                    "event_type": row.event_type,
                    "occurred_at": row.occurred_at.isoformat(),
                    "entity_id": str(row.entity_id),
                    "tracking_id": row.tracking_id or "",
                    "payload": json.dumps(row.payload),
                }

            try:
                msg_id = await self.client.xadd(
                    target_stream,
                    payload_fields,
                    max_len=self.maxlen,
                    approximate=True,
                )
                row.status = "PUBLISHED"
                row.published_at = datetime.now(timezone.utc)
                row.last_error = None
                published_count += 1
                logger.info(
                    "Outbox worker published event %s (%s) to %s: %s",
                    row.event_id,
                    row.event_type,
                    target_stream,
                    msg_id,
                )
            except Exception as e:
                row.attempts += 1
                row.last_error = str(e)[:1000]
                failed_count += 1
                logger.warning(
                    "Outbox publish failed for event %s (attempt %d/%d): %s",
                    row.event_id,
                    row.attempts,
                    row.max_attempts,
                    e,
                )

                if row.attempts >= row.max_attempts:
                    row.status = "DEAD_LETTER"
                    logger.error(
                        "Outbox event %s reached max attempts (%d); moved to DEAD_LETTER",
                        row.event_id,
                        row.max_attempts,
                    )
                else:
                    delay_seconds = min(300, 2**row.attempts)
                    row.next_retry_at = datetime.now(timezone.utc) + timedelta(
                        seconds=delay_seconds
                    )

        await session.commit()
        return published_count, failed_count

    async def publish_outbox_record(
        self,
        session: AsyncSession,
        outbox_id: str,
    ) -> bool:
        """Fast-path attempt to publish a single outbox record immediately after domain commit."""
        stmt = (
            select(RealtimeOutbox)
            .where(RealtimeOutbox.id == outbox_id, RealtimeOutbox.status == "PENDING")
            .with_for_update(skip_locked=True)
        )
        res = await session.execute(stmt)
        row = res.scalar_one_or_none()
        if row is None:
            return False

        if row.event_type.startswith("orchestration."):
            target_stream = "stream:weather:orchestration"
            orch_dict = row.payload
            payload_fields = {
                "event_id": str(orch_dict.get("event_id", row.event_id)),
                "event_type": orch_dict.get("event_type", row.event_type),
                "aggregate_type": orch_dict.get("aggregate_type", ""),
                "aggregate_id": orch_dict.get("aggregate_id", row.entity_id),
                "correlation_id": orch_dict.get("correlation_id", ""),
                "attempt": str(orch_dict.get("attempt", row.attempts + 1)),
                "data": json.dumps(orch_dict),
            }
        else:
            target_stream = self.stream_name
            payload_fields = {
                "event_id": str(row.event_id),
                "event_type": row.event_type,
                "occurred_at": row.occurred_at.isoformat(),
                "entity_id": str(row.entity_id),
                "tracking_id": row.tracking_id or "",
                "payload": json.dumps(row.payload),
            }

        try:
            await self.client.xadd(
                target_stream,
                payload_fields,
                max_len=self.maxlen,
                approximate=True,
            )
            row.status = "PUBLISHED"
            row.published_at = datetime.now(timezone.utc)
            row.last_error = None
            await session.commit()
            return True
        except Exception as e:
            row.attempts += 1
            row.last_error = str(e)[:1000]
            delay_seconds = min(300, 2**row.attempts)
            row.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
            await session.commit()
            logger.warning(
                "Fast-path outbox publish failed for event %s; queued for background worker: %s",
                row.event_id,
                e,
            )
            return False

    async def prune_published_events(
        self,
        session: AsyncSession,
        retention_hours: int = 72,
    ) -> int:
        """Prune historical published events older than retention_hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
        stmt = delete(RealtimeOutbox).where(
            RealtimeOutbox.status == "PUBLISHED",
            RealtimeOutbox.published_at < cutoff,
        )
        res = await session.execute(stmt)
        await session.commit()
        deleted_count = int(getattr(res, "rowcount", 0) or 0)
        if deleted_count > 0:
            logger.info("Pruned %d published outbox records older than %s", deleted_count, cutoff)
        return deleted_count

    async def run_loop(
        self,
        poll_interval: Optional[float] = None,
        batch_size: Optional[int] = None,
        prune_interval: Optional[int] = None,
        retention_hours: Optional[int] = None,
        stop_event: Optional[asyncio.Event] = None,
    ) -> None:
        """Run the continuous outbox worker processing and periodic pruning loop."""
        interval = (
            poll_interval
            if poll_interval is not None
            else settings.OUTBOX_WORKER_POLL_INTERVAL_SECONDS
        )
        batch = batch_size if batch_size is not None else settings.OUTBOX_WORKER_BATCH_SIZE
        prune_sec = (
            prune_interval
            if prune_interval is not None
            else settings.OUTBOX_WORKER_PRUNE_INTERVAL_SECONDS
        )
        retention = (
            retention_hours
            if retention_hours is not None
            else settings.OUTBOX_WORKER_RETENTION_HOURS
        )

        if not settings.OUTBOX_WORKER_ENABLED:
            logger.info(
                "RealtimeOutboxWorker is disabled by configuration "
                "(OUTBOX_WORKER_ENABLED=false); exiting loop"
            )
            return

        logger.info(
            "Starting RealtimeOutboxWorker loop "
            "(poll_interval=%.2fs, batch_size=%d, prune_interval=%ds, retention=%dh)",
            interval,
            batch,
            prune_sec,
            retention,
        )

        last_prune_time = datetime.now(timezone.utc)

        while stop_event is None or not stop_event.is_set():
            try:
                # 1. Periodic pruning of historical published events
                now = datetime.now(timezone.utc)
                if (now - last_prune_time).total_seconds() >= prune_sec:
                    async with self.session_factory() as session:
                        await self.prune_published_events(session, retention_hours=retention)
                    last_prune_time = now

                # 2. Process batch of pending outbox rows
                async with self.session_factory() as session:
                    published_count, failed_count = await self.publish_pending_batch(
                        session=session,
                        batch_size=batch,
                    )

                # 3. If work was done, immediately continue to next iteration to drain backlog
                if published_count > 0:
                    continue

                # 4. If no work was done, wait for poll_interval or stop_event
                if stop_event is not None:
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=interval)
                        break
                    except asyncio.TimeoutError:
                        pass
                else:
                    await asyncio.sleep(interval)

            except asyncio.CancelledError:
                logger.info("RealtimeOutboxWorker loop received cancellation signal")
                break
            except Exception as e:
                logger.error(
                    "Unexpected error in RealtimeOutboxWorker loop; sleeping %.2fs: %s",
                    interval,
                    e,
                    exc_info=True,
                )
                if stop_event is not None:
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=interval)
                        break
                    except asyncio.TimeoutError:
                        pass
                else:
                    await asyncio.sleep(interval)

        logger.info("RealtimeOutboxWorker loop stopped cleanly")


outbox_worker = RealtimeOutboxWorker()
