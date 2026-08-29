import asyncio
import hashlib
import html
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

from app.core.config import settings
from app.ingestion.exceptions import AdapterFetchError, NormalizationError
from app.ingestion.schemas import NormalizedEvidenceEvent, RawIngestionEvent

logger = logging.getLogger(__name__)


class GDELTNewsAdapter:
    """Ingestion adapter for global web news and secondary evidence via GDELT DOC 2.0 API.

    Semantic Principles:
    1. Source Country != Event Country:
       `sourcecountry:IN` filters for articles published by outlets originating in India.
       It does NOT prove or imply that the weather event occurred inside India (e.g. Indian
       outlets reporting on Nepal or Bangladesh floods). The adapter preserves `sourcecountry`
       strictly as source metadata in `raw_payload`, without fabricating incident coordinates
       or declaring the event as Indian.
    2. Seendate != Event Occurred At:
       GDELT `seendate` is when the crawler indexed the article, NOT the physical incident time.
       It is normalized to `published_at` as evidence metadata and never as `occurred_at`.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        query: Optional[str] = None,
        max_records: Optional[int] = None,
        timespan: Optional[str] = None,
        min_interval_seconds: Optional[float] = None,
        timeout_seconds: Optional[float] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.source_code = "GDELT_DOC"
        self.source_name = "GDELT DOC 2.0 Web News"
        self.source_type = "RSS"
        self.base_trust_score = 0.70

        self.endpoint = endpoint or settings.GDELT_DOC_ENDPOINT
        self.query = query or settings.GDELT_QUERY
        self.max_records = max_records or settings.GDELT_MAX_RECORDS
        self.timespan = timespan or settings.GDELT_TIMESPAN
        self.min_interval_seconds = (
            min_interval_seconds
            if min_interval_seconds is not None
            else settings.GDELT_MIN_REQUEST_INTERVAL_SECONDS
        )
        self.timeout_seconds = timeout_seconds or settings.GDELT_REQUEST_TIMEOUT_SECONDS
        self._http_client = http_client
        self._last_request_time: float = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client and not self._http_client.is_closed:
            return self._http_client
        return httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout_seconds),
            headers={"User-Agent": "NationalWeatherPlatform-GDELT/1.0"},
            verify=False,
            follow_redirects=True,
        )

    async def _apply_rate_limit(self) -> None:
        """Enforce polite minimum request interval to comply with GDELT API policies."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self.min_interval_seconds:
            wait_time = self.min_interval_seconds - elapsed
            logger.debug(f"GDELT rate throttle: waiting {wait_time:.2f}s before request")
            await asyncio.sleep(wait_time)
        self._last_request_time = time.monotonic()

    @staticmethod
    def canonicalize_url(url: str) -> str:
        """Strip tracking query parameters and trailing slashes to generate a canonical URL."""
        if not url:
            return ""
        parsed = urlparse(url.strip())
        # Filter out common analytics query parameters
        tracking_prefixes = ("utm_", "fbclid", "gclid", "ref", "ref_", "mc_")
        filtered_queries = [
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if not any(k.lower().startswith(prefix) for prefix in tracking_prefixes)
        ]
        new_query = urlencode(filtered_queries)
        clean_path = parsed.path.rstrip("/") if parsed.path != "/" else "/"
        canonical = urlunparse(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                clean_path,
                parsed.params,
                new_query,
                "",  # strip fragment
            )
        )
        return canonical

    async def fetch_raw_events(
        self,
        query: Optional[str] = None,
        max_records: Optional[int] = None,
        timespan: Optional[str] = None,
    ) -> List[RawIngestionEvent]:
        """Fetch raw article records from GDELT DOC 2.0 ArtList endpoint."""
        target_query = query or self.query
        target_max = max_records or self.max_records
        target_timespan = timespan or self.timespan

        params: Dict[str, Any] = {
            "query": target_query,
            "mode": "ArtList",
            "format": "json",
            "sort": "DateDesc",
            "maxrecords": target_max,
            "timespan": target_timespan,
        }

        await self._apply_rate_limit()

        client = await self._get_client()
        should_close = client != self._http_client

        try:
            response = await client.get(self.endpoint, params=params)
            if response.status_code != 200:
                truncated = response.text[:200]
                raise AdapterFetchError(
                    f"GDELT API returned HTTP {response.status_code}: {truncated}",
                    source_code=self.source_code,
                )

            try:
                data = response.json()
            except Exception as e:
                # Handle possible non-JSON response on empty or error results
                raise AdapterFetchError(
                    f"Failed to decode GDELT JSON response: {e} ({response.text[:100]})",
                    source_code=self.source_code,
                )

            articles = data.get("articles", [])
            raw_events: List[RawIngestionEvent] = []

            for article in articles:
                raw_url = str(article.get("url") or article.get("url_mobile") or "").strip()
                if not raw_url:
                    continue

                canonical = self.canonicalize_url(raw_url)
                url_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                ext_id = f"GDELT-{url_hash}"

                raw_events.append(
                    RawIngestionEvent(
                        source_code=self.source_code,
                        external_id=ext_id,
                        payload=article,
                    )
                )

            logger.info(f"Fetched {len(raw_events)} raw evidence articles from GDELT DOC 2.0")
            return raw_events

        except (httpx.TimeoutException, httpx.RequestError) as e:
            raise AdapterFetchError(
                f"Network communication error contacting GDELT API: {e}",
                source_code=self.source_code,
            )
        finally:
            if should_close:
                await client.aclose()

    def parse_article(self, article: Dict[str, Any]) -> NormalizedEvidenceEvent:
        """Parse and normalize an individual GDELT article record into NormalizedEvidenceEvent."""
        raw_url = str(article.get("url") or article.get("url_mobile") or "").strip()
        if not raw_url:
            raise NormalizationError("Missing required 'url' in GDELT article", field="url")

        canonical_url = self.canonicalize_url(raw_url)
        sha256_hash = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
        external_id = f"GDELT-{sha256_hash}"

        title_raw = str(article.get("title") or "").strip()
        if not title_raw:
            raise NormalizationError("Missing required 'title' in GDELT article", field="title")
        # Unescape HTML entities in title
        title = html.unescape(title_raw)
        title = re.sub(r"\s+", " ", title).strip()

        domain = str(article.get("domain") or "").strip()
        if not domain and canonical_url:
            domain = urlparse(canonical_url).netloc.lower()

        language = str(article.get("language") or "English").strip()

        # Parse publication date (seendate format: "20260829T083000Z" or ISO)
        seendate_raw = str(article.get("seendate") or "").strip()
        published_at: Optional[datetime] = None
        if seendate_raw:
            try:
                published_at = datetime.strptime(seendate_raw, "%Y%m%dT%H%M%SZ").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                try:
                    published_at = datetime.fromisoformat(seendate_raw.replace("Z", "+00:00"))
                    if published_at.tzinfo is None:
                        published_at = published_at.replace(tzinfo=timezone.utc)
                except ValueError:
                    logger.warning(f"Could not parse GDELT seendate '{seendate_raw}'")

        # Snippet/Description if present (GDELT does not provide full body in ArtList)
        text_snippet = article.get("excerpt") or article.get("snippet")
        if text_snippet:
            text_snippet = html.unescape(str(text_snippet)).strip()

        return NormalizedEvidenceEvent(
            source_code=self.source_code,
            external_id=external_id,
            evidence_type="NEWS_ARTICLE",
            title=title,
            url=canonical_url,
            publisher_domain=domain or None,
            language=language or "English",
            published_at=published_at,
            text_snippet=text_snippet,
            sha256_hash=sha256_hash,
            raw_payload=article,
        )

    async def normalize(self, raw_event: RawIngestionEvent) -> NormalizedEvidenceEvent:
        """Convert a raw GDELT payload into a standardized NormalizedEvidenceEvent."""
        return self.parse_article(raw_event.payload)

    async def ingest(self) -> List[NormalizedEvidenceEvent]:
        """Execute complete fetch and normalization cycle for GDELT web news evidence."""
        raw_events = await self.fetch_raw_events()
        normalized_evidence: List[NormalizedEvidenceEvent] = []

        for raw in raw_events:
            try:
                norm = await self.normalize(raw)
                normalized_evidence.append(norm)
            except Exception as e:
                logger.warning(
                    f"Skipping malformed GDELT article '{raw.external_id}': {e}",
                    extra={"source": self.source_code, "raw_id": raw.external_id},
                )

        logger.info(
            f"Normalized {len(normalized_evidence)}/{len(raw_events)} GDELT evidence articles"
        )
        return normalized_evidence
