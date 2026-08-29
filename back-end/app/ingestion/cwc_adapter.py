import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.ingestion.exceptions import AdapterFetchError, NormalizationError
from app.ingestion.schemas import NormalizedObservationEvent, RawIngestionEvent

logger = logging.getLogger(__name__)


class CWCTelemetryAdapter:
    """Ingestion adapter for Central Water Commission (CWC) River Telemetry via NWDP CKAN."""

    def __init__(
        self,
        api_endpoint: Optional[str] = None,
        resource_id: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        fetch_limit: Optional[int] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.source_code = "CWC_NWDP"
        self.source_name = "Central Water Commission River Telemetry (NWDP)"
        self.source_type = "GOV_OPEN_DATA"
        self.base_trust_score = 0.92

        self.api_endpoint = api_endpoint or settings.CWC_NWDP_API_ENDPOINT
        self.resource_id = resource_id or settings.CWC_NWDP_RESOURCE_ID
        self.timeout_seconds = timeout_seconds or settings.CWC_REQUEST_TIMEOUT_SECONDS
        self.fetch_limit = fetch_limit or settings.CWC_FETCH_LIMIT
        self._http_client = http_client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client and not self._http_client.is_closed:
            return self._http_client
        return httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout_seconds),
            headers={"User-Agent": "NationalWeatherPlatform-CWC/1.0"},
            verify=False,
            follow_redirects=True,
        )

    async def fetch_raw_events(
        self,
        resource_id: Optional[str] = None,
        limit: Optional[int] = None,
        sort: str = "_id desc",
    ) -> List[RawIngestionEvent]:
        """Query the CKAN datastore_search API for CWC river water level telemetry records."""
        target_resource = resource_id or self.resource_id
        target_limit = limit or self.fetch_limit

        params: Dict[str, Any] = {
            "resource_id": target_resource,
            "limit": target_limit,
            "sort": sort,
        }

        client = await self._get_client()
        should_close = client != self._http_client

        try:
            response = await client.get(self.api_endpoint, params=params)
            if response.status_code != 200:
                truncated = response.text[:200]
                raise AdapterFetchError(
                    f"CWC/NWDP CKAN datastore returned HTTP {response.status_code}: {truncated}",
                    source_code=self.source_code,
                )

            try:
                data = response.json()
            except Exception as e:
                raise AdapterFetchError(
                    f"Failed to decode CWC/NWDP JSON response: {e}",
                    source_code=self.source_code,
                )

            if not data.get("success", False):
                err_msg = data.get("error", {}).get("message", "Unknown CKAN error")
                raise AdapterFetchError(
                    f"CWC/NWDP CKAN query failed: {err_msg}",
                    source_code=self.source_code,
                )

            records = data.get("result", {}).get("records", [])
            raw_events: List[RawIngestionEvent] = []

            for record in records:
                # Generate deterministic external ID
                station_name = str(record.get("Station") or "UNKNOWN").strip()
                basin_name = str(record.get("Basin") or "UNKNOWN").strip()
                acq_time = str(record.get("Data Acquisition Time") or "").strip()

                clean_basin = re.sub(r"[^A-Z0-9]", "", basin_name.upper()) or "GEN"
                clean_station = re.sub(r"[^A-Z0-9]", "", station_name.upper()) or "STA"
                clean_time = re.sub(r"[^0-9]", "", acq_time) or "00000000"

                ext_id = f"CWC-{clean_basin}-{clean_station}-{clean_time}"

                raw_events.append(
                    RawIngestionEvent(
                        source_code=self.source_code,
                        external_id=ext_id,
                        payload=record,
                    )
                )

            logger.info(
                f"Fetched {len(raw_events)} raw telemetry records from CWC/NWDP "
                f"(resource: {target_resource})"
            )
            return raw_events

        except (httpx.TimeoutException, httpx.RequestError) as e:
            raise AdapterFetchError(
                f"Network communication error contacting CWC/NWDP API: {e}",
                source_code=self.source_code,
            )
        finally:
            if should_close:
                await client.aclose()

    def parse_record(self, record: Dict[str, Any]) -> NormalizedObservationEvent:
        """Parse and normalize an individual CWC datastore telemetry record."""
        # 1. Station Name & Identity
        station_name = str(record.get("Station") or "").strip()
        if not station_name or station_name == "-":
            raise NormalizationError(
                "Missing required 'Station' field in CWC record", field="station_name"
            )

        basin_name = str(record.get("Basin") or "").strip()
        clean_basin = re.sub(r"[^A-Z0-9]", "", basin_name.upper()) or "GEN"
        clean_station = re.sub(r"[^A-Z0-9]", "", station_name.upper())
        station_code = f"CWC-{clean_basin}-{clean_station}"

        # 2. Coordinates
        lat_raw = record.get("Latitude")
        lon_raw = record.get("Longitude")
        if lat_raw is None or lon_raw is None or str(lat_raw).strip() in ("", "-"):
            raise NormalizationError(
                f"Missing coordinates for CWC station '{station_name}'", field="geom"
            )

        try:
            latitude = float(str(lat_raw).strip())
            longitude = float(str(lon_raw).strip())
        except (ValueError, TypeError):
            raise NormalizationError(
                f"Invalid coordinate numbers (lat='{lat_raw}', lon='{lon_raw}')", field="geom"
            )

        if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
            raise NormalizationError(
                f"Coordinates out of bounds ({latitude}, {longitude})", field="geom"
            )

        # 3. Data Acquisition Timestamp
        time_raw = str(record.get("Data Acquisition Time") or "").strip()
        if not time_raw or time_raw == "-":
            raise NormalizationError(
                f"Missing timestamp for CWC station '{station_name}'", field="observed_at"
            )

        try:
            # Expected format: "27-08-2026 23:00" in Indian Standard Time (IST / UTC+05:30)
            naive_dt = datetime.strptime(time_raw, "%d-%m-%Y %H:%M")
            ist_tz = timezone(timedelta(hours=5, minutes=30))
            observed_at = naive_dt.replace(tzinfo=ist_tz).astimezone(timezone.utc)
        except ValueError:
            # Fallback to ISO or alternative format
            try:
                observed_at = datetime.fromisoformat(time_raw.replace("Z", "+00:00"))
                if observed_at.tzinfo is None:
                    observed_at = observed_at.replace(tzinfo=timezone.utc)
            except ValueError:
                raise NormalizationError(
                    f"Unrecognized CWC timestamp format: '{time_raw}'", field="observed_at"
                )

        # 4. Water Level (meters)
        water_level_m: Optional[float] = None
        wl_candidates = [
            record.get("River Water Level Telemetry Hourly (meter)"),
            record.get("River Water Level (meter)"),
            record.get("water_level_m"),
            record.get("Water Level (m)"),
        ]
        for candidate in wl_candidates:
            if candidate is not None:
                cand_str = str(candidate).strip()
                if cand_str and cand_str not in ("-", "NA", "N/A", "null"):
                    try:
                        water_level_m = float(cand_str)
                        break
                    except (ValueError, TypeError):
                        pass

        # 5. External ID
        # Format: CWC-{BASIN}-{STATION}-{YYYYMMDDHHMM} (in UTC)
        external_id = f"{station_code}-{observed_at.strftime('%Y%m%d%H%M')}"

        # 6. Raw Metrics & Metadata
        raw_metrics: Dict[str, Any] = {
            "river": record.get("River"),
            "basin": record.get("Basin"),
            "tributary": record.get("Tributary"),
            "local_river": record.get("Local River"),
            "state": record.get("State"),
            "district": record.get("District"),
            "tehsil": record.get("Tehsil"),
            "rl_of_zero_gauge": record.get("RL_of_zeroGauge"),
            "mean_sea_level": record.get("MeanSeaLevel"),
            "is_discharge_available": record.get("Is_DischargeDataAvailable"),
            "state_lgd_code": record.get("State LGD Code"),
            "district_lgd_code": record.get("District LGD Code"),
        }

        return NormalizedObservationEvent(
            source_code=self.source_code,
            external_id=external_id,
            station_code=station_code,
            station_name=station_name,
            latitude=latitude,
            longitude=longitude,
            observed_at=observed_at,
            water_level_m=water_level_m,
            raw_metrics=raw_metrics,
        )

    async def normalize(self, raw_event: RawIngestionEvent) -> NormalizedObservationEvent:
        """Convert a raw CWC payload into a standardized NormalizedObservationEvent."""
        return self.parse_record(raw_event.payload)

    async def ingest(self) -> List[NormalizedObservationEvent]:
        """Execute complete fetch and normalization cycle for CWC River Water Level telemetry."""
        raw_events = await self.fetch_raw_events()
        normalized_observations: List[NormalizedObservationEvent] = []

        for raw in raw_events:
            try:
                norm = await self.normalize(raw)
                normalized_observations.append(norm)
            except Exception as e:
                logger.warning(
                    f"Skipping malformed CWC observation '{raw.external_id}': {e}",
                    extra={"source": self.source_code, "raw_id": raw.external_id},
                )

        logger.info(f"Normalized {len(normalized_observations)}/{len(raw_events)} CWC observations")
        return normalized_observations
