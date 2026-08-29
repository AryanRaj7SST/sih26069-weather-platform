import asyncio
import hashlib
import html
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.ingestion.exceptions import AdapterFetchError, NormalizationError
from app.ingestion.schemas import NormalizedEvidenceEvent, RawIngestionEvent

logger = logging.getLogger(__name__)


class MastodonSocialAdapter:
    """Ingestion adapter for public weather and disaster social posts via Mastodon REST API.

    Semantic Principles:
    1. Secondary Evidence:
       Mastodon posts represent public, unverified social evidence ('SOCIAL_POST'). They are
       never converted directly into ground-truth WeatherReport incidents or official alerts.
    2. Zero Coordinate Fabrication:
       No GPS coordinates or geometry are fabricated from hashtags or instance domains.
    3. Public Visibility Only:
       Only posts with visibility == 'public' are ingested. Direct, unlisted, or private posts
       are strictly excluded.
    """

    def __init__(
        self,
        instance_url: Optional[str] = None,
        hashtags: Optional[List[str]] = None,
        max_results_per_tag: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        min_interval_seconds: Optional[float] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.source_code = "MASTODON_PUBLIC"
        self.source_name = "Mastodon Public Social Posts"
        self.source_type = "SOCIAL"
        self.base_trust_score = 0.60

        self.instance_url = (instance_url or settings.MASTODON_INSTANCE_URL).rstrip("/")
        self.hashtags = hashtags if hashtags is not None else list(settings.MASTODON_HASHTAGS)
        self.max_results_per_tag = max_results_per_tag or settings.MASTODON_MAX_RESULTS_PER_TAG
        self.timeout_seconds = timeout_seconds or settings.MASTODON_REQUEST_TIMEOUT_SECONDS
        self.min_interval_seconds = (
            min_interval_seconds
            if min_interval_seconds is not None
            else settings.MASTODON_MIN_REQUEST_INTERVAL_SECONDS
        )
        self._http_client = http_client
        self._last_request_time: float = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client and not self._http_client.is_closed:
            return self._http_client
        return httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout_seconds),
            headers={"User-Agent": "NationalWeatherPlatform-Mastodon/1.0"},
            verify=False,
            follow_redirects=True,
        )

    async def _apply_rate_limit(self, response: Optional[httpx.Response] = None) -> None:
        """Enforce rate limits dynamically based on headers and minimum request interval."""
        if response is not None:
            remaining = response.headers.get("x-ratelimit-remaining")
            reset_time = response.headers.get("x-ratelimit-reset")
            if remaining and remaining.isdigit() and int(remaining) <= 1 and reset_time:
                try:
                    # If reset_time is ISO timestamp or seconds
                    reset_dt = datetime.fromisoformat(reset_time.replace("Z", "+00:00"))
                    wait_sec = max(0.0, (reset_dt - datetime.now(timezone.utc)).total_seconds())
                    if wait_sec > 0:
                        logger.warning(
                            f"Mastodon rate limit nearly exhausted: sleeping {wait_sec:.2f}s"
                        )
                        await asyncio.sleep(wait_sec)
                except Exception:
                    pass

        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self.min_interval_seconds:
            wait_time = self.min_interval_seconds - elapsed
            await asyncio.sleep(wait_time)
        self._last_request_time = time.monotonic()

    @staticmethod
    def sanitize_html(html_text: str) -> str:
        """Strip HTML tags, unescape entities, and collapse whitespace."""
        if not html_text:
            return ""
        no_tags = re.sub(r"<[^>]+>", " ", html_text)
        unescaped = html.unescape(no_tags)
        clean = re.sub(r"\s+", " ", unescaped).strip()
        return clean

    @staticmethod
    def derive_title(clean_text: str) -> str:
        """Generate a neutral, descriptive short title from the status snippet."""
        if not clean_text:
            return "Mastodon public social post"
        if len(clean_text) <= 80:
            return f"Mastodon post: {clean_text}"
        return f"Mastodon post: {clean_text[:77]}..."

    async def fetch_hashtag_timeline(
        self,
        hashtag: str,
        limit: Optional[int] = None,
        since_id: Optional[str] = None,
        max_id: Optional[str] = None,
    ) -> List[RawIngestionEvent]:
        """Query the public hashtag timeline endpoint on the configured Mastodon instance."""
        clean_tag = hashtag.lstrip("#").strip()
        if not clean_tag:
            return []

        endpoint = f"{self.instance_url}/api/v1/timelines/tag/{clean_tag}"
        params: Dict[str, Any] = {
            "limit": limit or self.max_results_per_tag,
        }
        if since_id:
            params["since_id"] = since_id
        if max_id:
            params["max_id"] = max_id

        await self._apply_rate_limit()

        client = await self._get_client()
        should_close = client != self._http_client

        try:
            response = await client.get(endpoint, params=params)
            await self._apply_rate_limit(response)

            if response.status_code != 200:
                truncated = response.text[:200]
                raise AdapterFetchError(
                    f"Mastodon HTTP {response.status_code} for #{clean_tag}: {truncated}",
                    source_code=self.source_code,
                )

            try:
                statuses = response.json()
            except Exception as e:
                raise AdapterFetchError(
                    f"Failed to decode Mastodon JSON response for #{clean_tag}: {e}",
                    source_code=self.source_code,
                )

            if not isinstance(statuses, list):
                logger.warning(
                    f"Unexpected Mastodon response structure for #{clean_tag}: expected list"
                )
                return []

            raw_events: List[RawIngestionEvent] = []
            for status in statuses:
                if not isinstance(status, dict):
                    continue

                # Visibility Guard: strictly public posts only
                visibility = str(status.get("visibility") or "").lower()
                if visibility != "public":
                    continue

                raw_url = str(status.get("url") or status.get("uri") or "").strip()
                if not raw_url:
                    continue

                sha256_hash = hashlib.sha256(raw_url.encode("utf-8")).hexdigest()
                ext_id = f"MASTODON-{sha256_hash}"

                raw_events.append(
                    RawIngestionEvent(
                        source_code=self.source_code,
                        external_id=ext_id,
                        payload=status,
                    )
                )

            logger.info(f"Fetched {len(raw_events)} public statuses from Mastodon #{clean_tag}")
            return raw_events

        except (httpx.TimeoutException, httpx.RequestError) as e:
            raise AdapterFetchError(
                f"Network error querying Mastodon #{clean_tag}: {e}",
                source_code=self.source_code,
            )
        finally:
            if should_close:
                await client.aclose()

    async def fetch_raw_events(
        self,
        hashtags: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[RawIngestionEvent]:
        """Iterate configured hashtags and collect public raw social posts."""
        target_tags = hashtags or self.hashtags
        all_raw_events: List[RawIngestionEvent] = []
        seen_ext_ids = set()

        for tag in target_tags:
            try:
                events = await self.fetch_hashtag_timeline(tag, limit=limit)
                for ev in events:
                    if ev.external_id not in seen_ext_ids:
                        seen_ext_ids.add(ev.external_id)
                        all_raw_events.append(ev)
            except Exception as e:
                logger.warning(
                    f"Skipping failed Mastodon hashtag #{tag}: {e}",
                    extra={"source": self.source_code, "hashtag": tag},
                )

        logger.info(
            f"Collected {len(all_raw_events)} Mastodon posts across {len(target_tags)} tags"
        )
        return all_raw_events

    def parse_status(self, status: Dict[str, Any]) -> NormalizedEvidenceEvent:
        """Parse and normalize an individual public Mastodon status into NormalizedEvidenceEvent."""
        # 1. Visibility Guard
        visibility = str(status.get("visibility") or "").lower()
        if visibility != "public":
            raise NormalizationError(
                f"Non-public status visibility '{visibility}' cannot be ingested",
                field="visibility",
            )

        # 2. Canonical URL & External ID
        canonical_url = str(status.get("url") or status.get("uri") or "").strip()
        if not canonical_url:
            raise NormalizationError(
                "Missing required 'url' or 'uri' in Mastodon status", field="url"
            )

        sha256_hash = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
        external_id = f"MASTODON-{sha256_hash}"

        # 3. Content Sanitization & Title
        raw_html = str(status.get("content") or "")
        clean_text = self.sanitize_html(raw_html)
        title = self.derive_title(clean_text)

        # 4. Domain & Account
        parsed_url = urlparse(canonical_url)
        domain = parsed_url.netloc.lower() or urlparse(self.instance_url).netloc.lower()
        account_obj = status.get("account") or {}
        acct_handle = str(account_obj.get("acct") or "").strip()

        # 5. Language
        language = str(status.get("language") or "English").strip() or "English"

        # 6. Publication Timestamp (UTC)
        created_at_raw = str(status.get("created_at") or "").strip()
        published_at: Optional[datetime] = None
        if created_at_raw:
            try:
                published_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
            except ValueError:
                logger.warning(f"Could not parse Mastodon created_at '{created_at_raw}'")

        # 7. Media Metadata (metadata only, no binary media downloads)
        raw_media = status.get("media_attachments") or []
        media_metadata: List[Dict[str, Any]] = []
        for m in raw_media:
            if isinstance(m, dict):
                media_metadata.append(
                    {
                        "type": m.get("type"),
                        "preview_url": m.get("preview_url"),
                        "url": m.get("url"),
                        "description": m.get("description"),
                    }
                )

        # 8. Hashtags & Provenance Metadata
        tags_raw = status.get("tags") or []
        tag_names = [t.get("name") for t in tags_raw if isinstance(t, dict) and t.get("name")]

        raw_payload: Dict[str, Any] = {
            "status_id": status.get("id"),
            "uri": status.get("uri"),
            "instance_url": self.instance_url,
            "account_handle": acct_handle,
            "account_display_name": account_obj.get("display_name"),
            "tags": tag_names,
            "media_attachments": media_metadata,
            "reblogs_count": status.get("reblogs_count"),
            "favourites_count": status.get("favourites_count"),
        }

        return NormalizedEvidenceEvent(
            source_code=self.source_code,
            external_id=external_id,
            evidence_type="SOCIAL_POST",
            title=title,
            url=canonical_url,
            publisher_domain=domain or None,
            language=language,
            published_at=published_at,
            text_snippet=clean_text or None,
            sha256_hash=sha256_hash,
            raw_payload=raw_payload,
        )

    async def normalize(self, raw_event: RawIngestionEvent) -> NormalizedEvidenceEvent:
        """Convert a raw Mastodon payload into a standardized NormalizedEvidenceEvent."""
        return self.parse_status(raw_event.payload)

    async def ingest(self) -> List[NormalizedEvidenceEvent]:
        """Execute complete fetch and normalization cycle for public Mastodon social evidence."""
        raw_events = await self.fetch_raw_events()
        normalized_evidence: List[NormalizedEvidenceEvent] = []

        for raw in raw_events:
            try:
                norm = await self.normalize(raw)
                normalized_evidence.append(norm)
            except Exception as e:
                logger.warning(
                    f"Skipping malformed Mastodon status '{raw.external_id}': {e}",
                    extra={"source": self.source_code, "raw_id": raw.external_id},
                )

        logger.info(f"Normalized {len(normalized_evidence)}/{len(raw_events)} Mastodon posts")
        return normalized_evidence
