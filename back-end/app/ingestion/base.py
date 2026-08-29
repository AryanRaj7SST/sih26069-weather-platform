import logging
from abc import ABC, abstractmethod
from typing import List

from app.ingestion.normalizer import EventNormalizer
from app.ingestion.schemas import NormalizedIngestionEvent, RawIngestionEvent

logger = logging.getLogger(__name__)


class BaseIngestionAdapter(ABC):
    """Abstract base class for all pluggable weather & disaster data ingestion adapters."""

    def __init__(
        self,
        source_code: str,
        source_name: str,
        source_type: str = "EXTERNAL_FEED",
        base_trust_score: float = 0.5,
    ) -> None:
        self.source_code = source_code.strip().upper()
        self.source_name = source_name
        self.source_type = source_type
        self.base_trust_score = base_trust_score
        self.normalizer = EventNormalizer()

    @abstractmethod
    async def fetch_raw_events(self) -> List[RawIngestionEvent]:
        """Fetch raw event payloads from the external data source."""
        pass

    async def normalize(self, raw_event: RawIngestionEvent) -> NormalizedIngestionEvent:
        """Convert a raw event payload into a standardized NormalizedIngestionEvent."""
        return self.normalizer.normalize(raw_event)

    async def ingest(self) -> List[NormalizedIngestionEvent]:
        """Execute complete fetch and normalization cycle for this adapter."""
        raw_events = await self.fetch_raw_events()
        normalized_events: List[NormalizedIngestionEvent] = []

        for raw in raw_events:
            try:
                norm = await self.normalize(raw)
                normalized_events.append(norm)
            except Exception as e:
                logger.warning(
                    f"Skipping malformed event from source '{self.source_code}': {e}",
                    extra={"source": self.source_code, "raw_id": raw.external_id},
                )

        return normalized_events
