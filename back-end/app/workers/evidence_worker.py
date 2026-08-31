import asyncio
import logging
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import async_session_factory
from app.ingestion.schemas import NormalizedEvidenceEvent
from app.models.evidence import EvidenceItem
from app.services.evidence_service import EvidenceService, evidence_service
from app.services.stream_service import StreamService, stream_service

logger = logging.getLogger(__name__)


class EvidenceWorker:
    """Consumes normalized secondary evidence from Redis Streams and persists to PostgreSQL."""

    def __init__(
        self,
        stream_svc: Optional[StreamService] = None,
        ev_svc: Optional[EvidenceService] = None,
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
        consumer_name: str = "worker-ev-primary",
    ) -> None:
        self.stream_svc = stream_svc or stream_service
        self.ev_svc = ev_svc or evidence_service
        self.session_factory = session_factory or async_session_factory
        self.consumer_name = consumer_name

    async def process_evidence(
        self,
        session: AsyncSession,
        event: NormalizedEvidenceEvent,
    ) -> EvidenceItem:
        """Process and persist an individual normalized evidence item."""
        return await self.ev_svc.ingest_normalized_evidence(session, event)

    async def process_batch(
        self,
        count: int = 10,
        block_ms: Optional[int] = 1000,
        from_id: str = ">",
    ) -> List[Tuple[str, Optional[EvidenceItem]]]:
        """Fetch a batch of evidence items from Redis Stream, process each, and ACK."""
        evidence_items = await self.stream_svc.read_evidence(
            consumer_name=self.consumer_name,
            count=count,
            block_ms=block_ms,
            from_id=from_id,
        )

        results: List[Tuple[str, Optional[EvidenceItem]]] = []
        if not evidence_items:
            return results

        async with self.session_factory() as session:
            for msg_id, ev_event in evidence_items:
                try:
                    evidence = await self.process_evidence(session, ev_event)
                    await self.stream_svc.ack_evidence(msg_id)
                    results.append((msg_id, evidence))
                except Exception as e:
                    logger.error(
                        f"Failed to persist evidence from stream msg '{msg_id}': {e}",
                        exc_info=True,
                    )
                    # Note: Message remains unacknowledged in PEL for retry or DLQ routing
                    results.append((msg_id, None))

        return results

    async def run_loop(
        self,
        stop_event: Optional[asyncio.Event] = None,
        interval: float = 1.0,
        count: int = 10,
        block_ms: int = 2000,
    ) -> None:
        """Continuously process evidence from stream:weather:evidence until stop_event is set."""
        logger.info("Starting EvidenceWorker continuous polling loop...")
        while stop_event is None or not stop_event.is_set():
            try:
                await self.process_batch(count=count, block_ms=block_ms)
                if stop_event is not None:
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=interval)
                        break
                    except asyncio.TimeoutError:
                        pass
                else:
                    await asyncio.sleep(interval)
            except asyncio.CancelledError:
                logger.info("EvidenceWorker loop received cancellation signal")
                break
            except Exception as e:
                logger.error(
                    "Unexpected error in EvidenceWorker loop; sleeping %.2fs: %s",
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

        logger.info("EvidenceWorker loop stopped cleanly")


evidence_worker = EvidenceWorker()
