from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.ingestion.base import BaseIngestionAdapter
from app.ingestion.schemas import RawIngestionEvent


class DemoSeedAdapter(BaseIngestionAdapter):
    """Deterministic ingestion adapter for testing, demonstration, and pipeline verification."""

    def __init__(
        self,
        source_code: str = "DEMO_FEED",
        source_name: str = "Simulated Emergency Weather Feed",
        custom_events: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        super().__init__(
            source_code=source_code,
            source_name=source_name,
            source_type="SEED_DEMO",
            base_trust_score=0.75,
        )
        self.custom_events = custom_events

    async def fetch_raw_events(self) -> List[RawIngestionEvent]:
        """Generate or return test event payloads."""
        if self.custom_events is not None:
            return [
                RawIngestionEvent(
                    source_code=self.source_code,
                    external_id=ev.get("external_id") or ev.get("id"),
                    payload=ev,
                )
                for ev in self.custom_events
            ]

        # Default deterministic sample events
        now_utc = datetime.now(timezone.utc)
        sample_payloads = [
            {
                "external_id": "DEMO-MUMBAI-001",
                "title": "Severe Waterlogging along Western Express Highway",
                "description": "Flash flooding causing massive traffic congestion near Andheri.",
                "latitude": 19.1136,
                "longitude": 72.8697,
                "location_name": "Andheri East, Mumbai, Maharashtra",
                "severity": "HIGH",
                "category": "FLOOD_WATERLOGGING",
                "occurred_at": now_utc.isoformat(),
            },
            {
                "external_id": "DEMO-BENGALURU-002",
                "title": "Thunderstorm and Tree Fall near Indiranagar",
                "description": "High wind gusts and lightning leading to localized power outage.",
                "latitude": 12.9716,
                "longitude": 77.5946,
                "location_name": "Indiranagar, Bengaluru, Karnataka",
                "severity": "MODERATE",
                "category": "THUNDERSTORM_LIGHTNING",
                "occurred_at": now_utc.isoformat(),
            },
        ]

        return [
            RawIngestionEvent(
                source_code=self.source_code,
                external_id=str(p["external_id"]),
                payload=p,
            )
            for p in sample_payloads
        ]
