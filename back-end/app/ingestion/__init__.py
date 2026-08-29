from app.ingestion.base import BaseIngestionAdapter
from app.ingestion.demo_adapter import DemoSeedAdapter
from app.ingestion.exceptions import (
    AdapterFetchError,
    IngestionError,
    NormalizationError,
)
from app.ingestion.imd_adapter import IMDNowcastAdapter
from app.ingestion.ndma_adapter import NDMASachetAdapter
from app.ingestion.normalizer import EventNormalizer
from app.ingestion.registry import AdapterRegistry, adapter_registry
from app.ingestion.schemas import (
    NormalizedIngestionEvent,
    RawIngestionEvent,
)

# Register standard adapters
adapter_registry.register_factory("IMD_NOWCAST", lambda: IMDNowcastAdapter())
adapter_registry.register_factory("NDMA_SACHET", lambda: NDMASachetAdapter())

__all__ = [
    "BaseIngestionAdapter",
    "DemoSeedAdapter",
    "IMDNowcastAdapter",
    "NDMASachetAdapter",
    "EventNormalizer",
    "RawIngestionEvent",
    "NormalizedIngestionEvent",
    "IngestionError",
    "NormalizationError",
    "AdapterFetchError",
    "AdapterRegistry",
    "adapter_registry",
]
