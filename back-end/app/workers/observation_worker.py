import asyncio
import logging
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import async_session_factory
from app.ingestion.schemas import NormalizedObservationEvent
from app.models.observation import WeatherObservation
from app.services.observation_service import ObservationService, observation_service
from app.services.stream_service import StreamService, stream_service

logger = logging.getLogger(__name__)


class ObservationWorker:
    """Consumes normalized sensor observations from Redis Streams and persists them."""

    def __init__(
        self,
        stream_svc: Optional[StreamService] = None,
        obs_svc: Optional[ObservationService] = None,
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
        consumer_name: str = "worker-obs-primary",
    ) -> None:
        self.stream_svc = stream_svc or stream_service
        self.obs_svc = obs_svc or observation_service
        self.session_factory = session_factory or async_session_factory
        self.consumer_name = consumer_name

    async def process_observation(
        self,
        session: AsyncSession,
        event: NormalizedObservationEvent,
    ) -> WeatherObservation:
        """Process and persist an individual normalized sensor observation."""
        return await self.obs_svc.ingest_normalized_observation(session, event)

    async def process_batch(
        self,
        count: int = 10,
        block_ms: Optional[int] = 1000,
        from_id: str = ">",
    ) -> List[Tuple[str, Optional[WeatherObservation]]]:
        """Fetch a batch of observations from Redis Stream, process each, and ACK."""
        observations = await self.stream_svc.read_observations(
            consumer_name=self.consumer_name,
            count=count,
            block_ms=block_ms,
            from_id=from_id,
        )

        results: List[Tuple[str, Optional[WeatherObservation]]] = []
        if not observations:
            return results

        async with self.session_factory() as session:
            for msg_id, obs_event in observations:
                try:
                    observation = await self.process_observation(session, obs_event)
                    await self.stream_svc.ack_observation(msg_id)
                    results.append((msg_id, observation))
                except Exception as e:
                    logger.error(
                        f"Failed to persist observation from stream msg '{msg_id}': {e}",
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
        """Continuously process observations from observation stream until stop_event is set."""
        logger.info("Starting ObservationWorker continuous polling loop...")
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
                logger.info("ObservationWorker loop received cancellation signal")
                break
            except Exception as e:
                logger.error(
                    "Unexpected error in ObservationWorker loop; sleeping %.2fs: %s",
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

        logger.info("ObservationWorker loop stopped cleanly")


observation_worker = ObservationWorker()
