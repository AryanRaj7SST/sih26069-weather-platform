import json
import logging
from typing import List, Optional, Tuple

from app.core.redis import AsyncRedisClient, redis_client
from app.ingestion.schemas import NormalizedIngestionEvent, NormalizedObservationEvent

logger = logging.getLogger(__name__)


class StreamService:
    """Service abstraction for publishing and consuming normalized events over Redis Streams."""

    DEFAULT_STREAM = "stream:weather:events"
    DEFAULT_GROUP = "group:weather:processors"

    DEFAULT_OBSERVATION_STREAM = "stream:weather:observations"
    DEFAULT_OBSERVATION_GROUP = "group:weather:observation_processors"

    def __init__(self, client: Optional[AsyncRedisClient] = None) -> None:
        self.client = client or redis_client

    async def publish_event(
        self,
        event: NormalizedIngestionEvent,
        stream_name: Optional[str] = None,
    ) -> str:
        """Publish a normalized ingestion event payload to a Redis Stream."""
        stream = stream_name or self.DEFAULT_STREAM
        event_dict = event.model_dump(mode="json")
        payload_fields = {
            "event_id": str(event.event_id),
            "source_code": event.source_code,
            "external_id": event.external_id or "",
            "category_code": event.category_code or "OTHER",
            "severity": event.severity,
            "title": event.title,
            "occurred_at": event.occurred_at.isoformat(),
            "data": json.dumps(event_dict),
        }

        try:
            msg_id = await self.client.xadd(stream, payload_fields)
            logger.info(
                f"Published event '{event.event_id}' ({event.source_code}) to '{stream}': {msg_id}"
            )
            return msg_id
        except Exception as e:
            logger.error(f"Failed to publish ingestion event to Redis Stream '{stream}': {e}")
            raise

    async def publish_observation(
        self,
        observation: NormalizedObservationEvent,
        stream_name: Optional[str] = None,
    ) -> str:
        """Publish a normalized observation payload to the observation Redis Stream."""
        stream = stream_name or self.DEFAULT_OBSERVATION_STREAM
        obs_dict = observation.model_dump(mode="json")
        payload_fields = {
            "event_id": str(observation.event_id),
            "source_code": observation.source_code,
            "external_id": observation.external_id or "",
            "station_code": observation.station_code,
            "station_name": observation.station_name,
            "observed_at": observation.observed_at.isoformat(),
            "data": json.dumps(obs_dict),
        }

        try:
            msg_id = await self.client.xadd(stream, payload_fields)
            logger.info(
                f"Published observation '{observation.event_id}' "
                f"({observation.station_code}) to '{stream}': {msg_id}"
            )
            return msg_id
        except Exception as e:
            logger.error(f"Failed to publish observation to Redis Stream '{stream}': {e}")
            raise

    async def ensure_consumer_group(
        self,
        stream_name: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> bool:
        """Ensure a consumer group exists on the target stream."""
        stream = stream_name or self.DEFAULT_STREAM
        group = group_name or self.DEFAULT_GROUP
        return await self.client.xgroup_create(stream, group, id_str="0", mkstream=True)

    async def read_events(
        self,
        group_name: Optional[str] = None,
        consumer_name: str = "worker-1",
        count: int = 10,
        block_ms: Optional[int] = 2000,
        stream_name: Optional[str] = None,
        from_id: str = ">",
    ) -> List[Tuple[str, NormalizedIngestionEvent]]:
        """Read a batch of events from the stream for this consumer group."""
        stream = stream_name or self.DEFAULT_STREAM
        group = group_name or self.DEFAULT_GROUP

        await self.ensure_consumer_group(stream, group)

        raw_results = await self.client.xreadgroup(
            group=group,
            consumer=consumer_name,
            streams={stream: from_id},
            count=count,
            block_ms=block_ms,
        )

        events: List[Tuple[str, NormalizedIngestionEvent]] = []
        for _, entries in raw_results:
            for msg_id, fields in entries:
                try:
                    if "data" in fields:
                        data_dict = json.loads(fields["data"])
                        event = NormalizedIngestionEvent.model_validate(data_dict)
                    else:
                        event = NormalizedIngestionEvent.model_validate(fields)
                    events.append((msg_id, event))
                except Exception as e:
                    logger.error(f"Failed to deserialize stream message '{msg_id}': {e}")
                    # Acknowledge unrecoverable malformed message so queue does not block
                    await self.client.xack(stream, group, msg_id)

        return events

    async def read_observations(
        self,
        group_name: Optional[str] = None,
        consumer_name: str = "worker-obs-1",
        count: int = 10,
        block_ms: Optional[int] = 2000,
        stream_name: Optional[str] = None,
        from_id: str = ">",
    ) -> List[Tuple[str, NormalizedObservationEvent]]:
        """Read a batch of observations from the observation stream for this consumer group."""
        stream = stream_name or self.DEFAULT_OBSERVATION_STREAM
        group = group_name or self.DEFAULT_OBSERVATION_GROUP

        await self.ensure_consumer_group(stream, group)

        raw_results = await self.client.xreadgroup(
            group=group,
            consumer=consumer_name,
            streams={stream: from_id},
            count=count,
            block_ms=block_ms,
        )

        observations: List[Tuple[str, NormalizedObservationEvent]] = []
        for _, entries in raw_results:
            for msg_id, fields in entries:
                try:
                    if "data" in fields:
                        data_dict = json.loads(fields["data"])
                        obs = NormalizedObservationEvent.model_validate(data_dict)
                    else:
                        obs = NormalizedObservationEvent.model_validate(fields)
                    observations.append((msg_id, obs))
                except Exception as e:
                    logger.error(
                        f"Failed to deserialize observation stream message '{msg_id}': {e}"
                    )
                    # Acknowledge unrecoverable malformed message so queue does not block
                    await self.client.xack(stream, group, msg_id)

        return observations

    async def get_pending_summary(
        self,
        stream_name: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> dict:
        """Fetch summary of pending unacknowledged messages in the consumer group PEL."""
        stream = stream_name or self.DEFAULT_STREAM
        group = group_name or self.DEFAULT_GROUP
        return await self.client.xpending(stream, group)

    async def ack_event(
        self,
        message_id: str,
        stream_name: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> bool:
        """Acknowledge a processed stream event."""
        stream = stream_name or self.DEFAULT_STREAM
        group = group_name or self.DEFAULT_GROUP
        ack_count = await self.client.xack(stream, group, message_id)
        return ack_count > 0

    async def ack_observation(
        self,
        message_id: str,
        stream_name: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> bool:
        """Acknowledge a processed observation stream event."""
        stream = stream_name or self.DEFAULT_OBSERVATION_STREAM
        group = group_name or self.DEFAULT_OBSERVATION_GROUP
        ack_count = await self.client.xack(stream, group, message_id)
        return ack_count > 0


stream_service = StreamService()
