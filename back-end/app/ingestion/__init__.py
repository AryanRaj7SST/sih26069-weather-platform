from app.ingestion.base import BaseIngestionAdapter
from app.ingestion.cwc_adapter import CWCTelemetryAdapter
from app.ingestion.demo_adapter import DemoSeedAdapter
from app.ingestion.exceptions import (
    AdapterFetchError,
    IngestionError,
    NormalizationError,
)
from app.ingestion.gdelt_adapter import GDELTNewsAdapter
from app.ingestion.imd_adapter import IMDNowcastAdapter
from app.ingestion.mastodon_adapter import MastodonSocialAdapter
from app.ingestion.ndma_adapter import NDMASachetAdapter
from app.ingestion.normalizer import EventNormalizer
from app.ingestion.registry import AdapterRegistry, adapter_registry
from app.ingestion.schemas import (
    NormalizedEvidenceEvent,
    NormalizedIngestionEvent,
    NormalizedObservationEvent,
    RawIngestionEvent,
)

# Register standard adapters
adapter_registry.register_factory("IMD_NOWCAST", lambda: IMDNowcastAdapter())
adapter_registry.register_factory("NDMA_SACHET", lambda: NDMASachetAdapter())
adapter_registry.register_factory("CWC_NWDP", lambda: CWCTelemetryAdapter())
adapter_registry.register_factory("GDELT_DOC", lambda: GDELTNewsAdapter())
adapter_registry.register_factory("MASTODON_PUBLIC", lambda: MastodonSocialAdapter())

__all__ = [
    "BaseIngestionAdapter",
    "DemoSeedAdapter",
    "IMDNowcastAdapter",
    "NDMASachetAdapter",
    "CWCTelemetryAdapter",
    "GDELTNewsAdapter",
    "MastodonSocialAdapter",
    "EventNormalizer",
    "RawIngestionEvent",
    "NormalizedIngestionEvent",
    "NormalizedObservationEvent",
    "NormalizedEvidenceEvent",
    "IngestionError",
    "NormalizationError",
    "AdapterFetchError",
    "AdapterRegistry",
    "adapter_registry",
]
