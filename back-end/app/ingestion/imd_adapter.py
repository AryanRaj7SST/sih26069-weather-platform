import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import httpx

from app.core.config import settings
from app.ingestion.base import BaseIngestionAdapter
from app.ingestion.exceptions import AdapterFetchError
from app.ingestion.schemas import RawIngestionEvent

logger = logging.getLogger(__name__)


class IMDNowcastAdapter(BaseIngestionAdapter):
    """Official India Meteorological Department (IMD) Nowcast & Weather Warnings Ingestion Adapter.

    Ingests short-term severe weather warnings, nowcast hazard alerts, and meteorological
    observations from the official IMD API platform (https://api.imd.gov.in/).
    """

    IMD_SEVERITY_MAP: Dict[str, str] = {
        # IMD 4-Stage Color Codes
        "red": "SEVERE",
        "orange": "HIGH",
        "amber": "HIGH",
        "yellow": "MODERATE",
        "green": "LOW",
        "white": "LOW",
        # Textual Severity / Warning Levels
        "critical": "SEVERE",
        "extreme": "SEVERE",
        "severe": "SEVERE",
        "very heavy": "SEVERE",
        "danger": "SEVERE",
        "heavy": "HIGH",
        "high": "HIGH",
        "moderate to heavy": "HIGH",
        "warning": "HIGH",
        "alert": "HIGH",
        "moderate": "MODERATE",
        "light to moderate": "MODERATE",
        "watch": "MODERATE",
        "low": "LOW",
        "light": "LOW",
        "very light": "LOW",
        "no warning": "LOW",
        "nil": "LOW",
        "advisory": "LOW",
    }

    IMD_CATEGORY_MAP: Dict[str, str] = {
        "rain": "HEAVY_RAINFALL",
        "rainfall": "HEAVY_RAINFALL",
        "downpour": "HEAVY_RAINFALL",
        "cloudburst": "HEAVY_RAINFALL",
        "flood": "FLOOD_WATERLOGGING",
        "waterlog": "FLOOD_WATERLOGGING",
        "inundation": "FLOOD_WATERLOGGING",
        "thunder": "THUNDERSTORM_LIGHTNING",
        "lightning": "THUNDERSTORM_LIGHTNING",
        "thunderstorm": "THUNDERSTORM_LIGHTNING",
        "squall": "THUNDERSTORM_LIGHTNING",
        "gusty": "THUNDERSTORM_LIGHTNING",
        "cyclone": "CYCLONE_GALE",
        "gale": "CYCLONE_GALE",
        "storm": "CYCLONE_GALE",
        "depression": "CYCLONE_GALE",
        "wind": "CYCLONE_GALE",
        "heat": "HEATWAVE",
        "heatwave": "HEATWAVE",
        "warm night": "HEATWAVE",
        "hail": "HAILSTORM",
        "hailstorm": "HAILSTORM",
        "landslide": "LANDSLIDE",
        "mudslide": "LANDSLIDE",
    }

    def __init__(
        self,
        source_code: str = "IMD_NOWCAST",
        source_name: str = "India Meteorological Department (Nowcast & Warnings)",
        endpoint_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        custom_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        super().__init__(
            source_code=source_code,
            source_name=source_name,
            source_type="GOVERNMENT_PORTAL",
            base_trust_score=0.90,  # Official national meteorological authority
        )
        base_endpoint = settings.IMD_API_ENDPOINT.rstrip("/")
        self.endpoint_url = endpoint_url or f"{base_endpoint}/districtnowcast"
        self.api_key = api_key if api_key is not None else settings.IMD_API_KEY
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else settings.IMD_REQUEST_TIMEOUT_SECONDS
        )
        self._custom_client = custom_client

    def _build_headers(self) -> Dict[str, str]:
        """Construct authentication and user-agent headers for IMD API."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "NationalWeatherPlatform-SIH26069/1.0",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @classmethod
    def map_imd_severity(cls, raw_severity: Optional[str]) -> str:
        """Deterministically map IMD color codes and textual warning levels to 4-tier domain."""
        if not raw_severity:
            return "MODERATE"
        clean = str(raw_severity).lower().strip()
        if clean in cls.IMD_SEVERITY_MAP:
            return cls.IMD_SEVERITY_MAP[clean]
        for key in sorted(cls.IMD_SEVERITY_MAP.keys(), key=len, reverse=True):
            if key in clean:
                return cls.IMD_SEVERITY_MAP[key]
        return "MODERATE"

    @classmethod
    def map_imd_category(cls, raw_hazard: Optional[str], description: str = "") -> str:
        """Deterministically map IMD hazard terms to standard multi-hazard taxonomy."""
        combined = f"{raw_hazard or ''} {description}".lower()
        for key in sorted(cls.IMD_CATEGORY_MAP.keys(), key=len, reverse=True):
            if key in combined:
                return cls.IMD_CATEGORY_MAP[key]
        return "OTHER"

    @classmethod
    def generate_external_id(cls, record: Dict[str, Any]) -> str:
        """Generate a deterministic, stable external identifier for an IMD event."""
        # 1. Use explicit unique identifier if provided by the source
        explicit_id = (
            record.get("id")
            or record.get("warning_id")
            or record.get("nowcast_id")
            or record.get("alert_id")
            or record.get("guid")
        )
        if explicit_id:
            return f"IMD-{str(explicit_id).strip()}"[:255]

        # 2. Deterministic composite rule: station/district + timestamp + hazard type
        location_part = (
            record.get("district_id")
            or record.get("station_id")
            or record.get("district_name")
            or record.get("station_name")
            or record.get("district")
            or "NATIONAL"
        )
        time_part = (
            record.get("issue_time")
            or record.get("timestamp")
            or record.get("date_time")
            or record.get("date")
            or record.get("valid_from")
            or datetime.now(timezone.utc).strftime("%Y%m%d%H")
        )
        hazard_part = (
            record.get("warning_type")
            or record.get("hazard")
            or record.get("weather_condition")
            or record.get("color_code")
            or "ALERT"
        )

        clean_loc = re.sub(r"[^a-zA-Z0-9]", "_", str(location_part).upper()).strip("_")
        clean_time = re.sub(r"[^a-zA-Z0-9]", "_", str(time_part)).strip("_")
        clean_hazard = re.sub(r"[^a-zA-Z0-9]", "_", str(hazard_part).upper()).strip("_")

        return f"IMD-{clean_loc}-{clean_time}-{clean_hazard}"[:255]

    def parse_single_record(self, record: Dict[str, Any]) -> RawIngestionEvent:
        """Transform a raw IMD JSON object into a platform RawIngestionEvent."""
        external_id = self.generate_external_id(record)

        # Extract location info
        district_name = (
            record.get("district_name")
            or record.get("district")
            or record.get("station_name")
            or record.get("station")
            or record.get("place")
        )
        state_name = record.get("state_name") or record.get("state")
        location_name = (
            f"{district_name}, {state_name}" if district_name and state_name else district_name
        )

        # Extract coordinates
        latitude = (
            record.get("latitude")
            or record.get("lat")
            or record.get("geo_lat")
            or (
                record.get("location", {}).get("lat")
                if isinstance(record.get("location"), dict)
                else None
            )
        )
        longitude = (
            record.get("longitude")
            or record.get("lon")
            or record.get("long")
            or record.get("geo_lon")
            or (
                record.get("location", {}).get("lon")
                if isinstance(record.get("location"), dict)
                else None
            )
        )

        # Extract hazard & severity
        hazard_name = (
            record.get("warning_type")
            or record.get("hazard")
            or record.get("weather_condition")
            or record.get("weather_desc")
            or "Weather Warning"
        )
        color_code = (
            record.get("color_code")
            or record.get("colour_code")
            or record.get("warning_level")
            or record.get("severity")
        )
        severity = self.map_imd_severity(color_code)

        description = (
            record.get("description")
            or record.get("instruction")
            or record.get("warning_text")
            or record.get("nowcast_text")
            or f"IMD {color_code or 'Weather'} Alert for {location_name or 'district'}"
        )
        category_code = self.map_imd_category(hazard_name, str(description))

        title = f"IMD Alert: {hazard_name} in {district_name or 'District'}"
        if len(title) > 255:
            title = title[:252] + "..."

        time_val = (
            record.get("issue_time")
            or record.get("timestamp")
            or record.get("date_time")
            or record.get("valid_from")
            or record.get("date")
        )

        payload: Dict[str, Any] = {
            "title": title,
            "description": description,
            "latitude": latitude,
            "longitude": longitude,
            "location_name": location_name,
            "severity": severity,
            "category_code": category_code,
            "occurred_at": time_val,
            "external_id": external_id,
            "imd_raw_record": record,
        }

        return RawIngestionEvent(
            source_code=self.source_code,
            external_id=external_id,
            payload=payload,
            ingested_at=datetime.now(timezone.utc),
        )

    def parse_source_response(
        self, raw_data: Union[List[Any], Dict[str, Any]]
    ) -> List[RawIngestionEvent]:
        """Extract and parse record list from diverse IMD response payload envelopes."""
        raw_items: List[Dict[str, Any]] = []

        if isinstance(raw_data, list):
            raw_items = [item for item in raw_data if isinstance(item, dict)]
        elif isinstance(raw_data, dict):
            # Check common government API envelope structures
            if "data" in raw_data and isinstance(raw_data["data"], list):
                raw_items = [item for item in raw_data["data"] if isinstance(item, dict)]
            elif "records" in raw_data and isinstance(raw_data["records"], list):
                raw_items = [item for item in raw_data["records"] if isinstance(item, dict)]
            elif "results" in raw_data and isinstance(raw_data["results"], list):
                raw_items = [item for item in raw_data["results"] if isinstance(item, dict)]
            elif "warnings" in raw_data and isinstance(raw_data["warnings"], list):
                raw_items = [item for item in raw_data["warnings"] if isinstance(item, dict)]
            else:
                # Single object response
                raw_items = [raw_data]

        events: List[RawIngestionEvent] = []
        for item in raw_items:
            try:
                event = self.parse_single_record(item)
                events.append(event)
            except Exception as e:
                logger.warning(
                    f"Skipping unparseable IMD item from '{self.source_code}': {e}",
                    extra={"source": self.source_code, "raw_item": item},
                )

        return events

    async def fetch_raw_events(self) -> List[RawIngestionEvent]:
        """Fetch raw warning and nowcast records from the official IMD API."""
        headers = self._build_headers()

        # If no API key is configured in development, log clear informational notice
        if not self.api_key:
            logger.info(
                f"IMD API polling skipped for '{self.source_code}': "
                f"IMD_API_KEY is not configured (awaiting official portal key/whitelisting)."
            )

        client = self._custom_client or httpx.AsyncClient(timeout=self.timeout_seconds)
        should_close_client = self._custom_client is None

        try:
            response = await client.get(self.endpoint_url, headers=headers)

            if response.status_code in (401, 403):
                logger.warning(
                    f"IMD API requires authentication / IP whitelisting. "
                    f"Endpoint: {self.endpoint_url}, Status: {response.status_code}"
                )
                raise AdapterFetchError(
                    f"Authentication required for IMD API (HTTP {response.status_code}).",
                    source_code=self.source_code,
                )

            if response.status_code == 429:
                logger.warning(
                    f"IMD API rate limit encountered (HTTP 429). Endpoint: {self.endpoint_url}"
                )
                raise AdapterFetchError(
                    "IMD API rate limit exceeded (HTTP 429).", source_code=self.source_code
                )

            if response.status_code >= 500:
                logger.error(
                    f"IMD API server error (HTTP {response.status_code}): {self.endpoint_url}"
                )
                raise AdapterFetchError(
                    f"IMD API server error (HTTP {response.status_code}).",
                    source_code=self.source_code,
                )

            response.raise_for_status()
            data = response.json()
            return self.parse_source_response(data)

        except httpx.TimeoutException as e:
            logger.warning(f"IMD API request timed out after {self.timeout_seconds}s: {e}")
            raise AdapterFetchError(f"IMD API request timeout: {e}", source_code=self.source_code)
        except httpx.ConnectError as e:
            logger.warning(f"IMD API connection failure: {e}")
            raise AdapterFetchError(f"IMD API connection failed: {e}", source_code=self.source_code)
        except Exception as e:
            if isinstance(e, AdapterFetchError):
                raise
            logger.error(f"Unexpected error during IMD ingestion fetch: {e}", exc_info=True)
            raise AdapterFetchError(
                f"Unexpected IMD fetch error: {e}", source_code=self.source_code
            )
        finally:
            if should_close_client:
                await client.aclose()
