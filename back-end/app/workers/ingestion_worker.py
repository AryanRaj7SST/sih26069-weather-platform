import logging
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import async_session_factory
from app.ingestion.schemas import NormalizedIngestionEvent
from app.models.report import WeatherReport
from app.services.report_service import ReportService, report_service
from app.services.stream_service import StreamService, stream_service

logger = logging.getLogger(__name__)


class IngestionWorker:
    """Consumes normalized events from Redis Streams, validates, and dispatches to persistence."""

    def __init__(
        self,
        stream_svc: Optional[StreamService] = None,
        report_svc: Optional[ReportService] = None,
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
        consumer_name: str = "worker-primary",
    ) -> None:
        self.stream_svc = stream_svc or stream_service
        self.report_svc = report_svc or report_service
        self.session_factory = session_factory or async_session_factory
        self.consumer_name = consumer_name

    async def process_event(
        self,
        session: AsyncSession,
        event: NormalizedIngestionEvent,
    ) -> WeatherReport:
        """Process an individual normalized event through the pipeline stages."""
        # 1. Validation & Cleansing (Already enforced via NormalizedIngestionEvent)
        # 2. Stage Hook: Future classification / NLP hook
        # 3. Stage Hook: Future deduplication / FastEmbed clustering hook
        # 4. Stage Hook: Future IMD AWS sensor corroboration hook
        # 5. Stage Hook: Future explainable credibility scoring hook
        # 6. Persistence & Idempotency dispatch
        report = await self.report_svc.ingest_normalized_event(session, event)
        logger.info(
            f"Processed ingestion event '{event.event_id}' -> Report '{report.tracking_id}'"
        )
        return report

    async def process_batch(
        self,
        count: int = 10,
        block_ms: Optional[int] = 1000,
        from_id: str = ">",
    ) -> List[Tuple[str, Optional[WeatherReport]]]:
        """Fetch a batch of events from Redis Stream, process each, and acknowledge messages."""
        events = await self.stream_svc.read_events(
            consumer_name=self.consumer_name,
            count=count,
            block_ms=block_ms,
            from_id=from_id,
        )

        results: List[Tuple[str, Optional[WeatherReport]]] = []
        if not events:
            return results

        async with self.session_factory() as session:
            for msg_id, event in events:
                try:
                    report = await self.process_event(session, event)
                    await self.stream_svc.ack_event(msg_id)
                    results.append((msg_id, report))
                except Exception as e:
                    logger.error(
                        f"Failed to process event from stream msg '{msg_id}': {e}", exc_info=True
                    )
                    # Note: Message remains unacknowledged in PEL for retry or DLQ routing
                    results.append((msg_id, None))

        return results


ingestion_worker = IngestionWorker()
