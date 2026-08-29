import hashlib
import time
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import pool, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.ingestion.exceptions import AdapterFetchError, NormalizationError
from app.ingestion.gdelt_adapter import GDELTNewsAdapter
from app.ingestion.registry import adapter_registry
from app.ingestion.schemas import NormalizedEvidenceEvent
from app.models.evidence import EvidenceItem
from app.services.evidence_service import EvidenceService
from app.services.stream_service import StreamService
from app.workers.evidence_worker import EvidenceWorker

# Sample synthetic GDELT DOC 2.0 JSON payload
SAMPLE_GDELT_RESPONSE = {
    "articles": [
        {
            "url": "https://www.thehindu.com/news/national/mumbai-rains-waterlogging-kurla/article12345.ece?utm_source=twitter&utm_medium=social",
            "url_mobile": "https://m.thehindu.com/news/national/mumbai-rains-waterlogging-kurla/article12345.ece",
            "title": "Severe waterlogging in Kurla &amp; Sion as heavy downpour lashes Mumbai",
            "seendate": "20260829T083000Z",
            "socialimage": "https://www.thehindu.com/img/mumbai_rain.jpg",
            "domain": "thehindu.com",
            "language": "English",
            "sourcecountry": "India",
        },
        {
            "url": "https://timesofindia.indiatimes.com/city/mumbai/high-tide-warning-issued/articleshow/98765.cms",
            "title": "High tide warning issued for coastal Maharashtra",
            "seendate": "20260829T091500Z",
            "domain": "timesofindia.indiatimes.com",
            "language": "English",
            "sourcecountry": "India",
        },
    ]
}


@pytest_asyncio.fixture
async def db_session():
    """Create an isolated async database session per test with NullPool."""
    test_engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session

    await test_engine.dispose()


def test_gdelt_adapter_registry_lookup():
    """Verify GDELT_DOC adapter registration in adapter registry."""
    adapter = adapter_registry.get("GDELT_DOC")
    assert adapter is not None
    assert isinstance(adapter, GDELTNewsAdapter)
    assert adapter.source_code == "GDELT_DOC"
    assert adapter.base_trust_score == 0.70


def test_gdelt_url_canonicalization():
    """Verify stripping of tracking parameters (utm_*, fbclid, ref) and trailing slashes."""
    raw_url = "https://example.com/news/mumbai-flood/?utm_source=twitter&utm_medium=feed&fbclid=12345#section2"
    canonical = GDELTNewsAdapter.canonicalize_url(raw_url)
    assert canonical == "https://example.com/news/mumbai-flood"

    # URL without params preserves path
    simple_url = "https://example.com/article/101/"
    assert GDELTNewsAdapter.canonicalize_url(simple_url) == "https://example.com/article/101"


def test_gdelt_parse_article_field_mapping():
    """Verify complete field normalization, HTML entity unescaping, and date parsing."""
    adapter = GDELTNewsAdapter()
    article = SAMPLE_GDELT_RESPONSE["articles"][0]
    norm = adapter.parse_article(article)

    assert norm.source_code == "GDELT_DOC"
    assert norm.evidence_type == "NEWS_ARTICLE"
    # Unescaped &amp; -> &
    assert "Kurla & Sion" in norm.title
    assert (
        norm.url
        == "https://www.thehindu.com/news/national/mumbai-rains-waterlogging-kurla/article12345.ece"
    )
    assert norm.publisher_domain == "thehindu.com"
    assert norm.language == "English"
    assert norm.published_at == datetime(2026, 8, 29, 8, 30, 0, tzinfo=timezone.utc)
    expected_hash = hashlib.sha256(norm.url.encode("utf-8")).hexdigest()
    assert norm.sha256_hash == expected_hash
    assert norm.external_id == f"GDELT-{expected_hash}"
    assert norm.raw_payload["sourcecountry"] == "India"


def test_gdelt_external_id_determinism_and_collision_safety():
    """Verify deterministic external IDs across duplicate and distinct URLs."""
    adapter = GDELTNewsAdapter()
    art1 = SAMPLE_GDELT_RESPONSE["articles"][0]
    art2 = SAMPLE_GDELT_RESPONSE["articles"][1]

    norm1 = adapter.parse_article(art1)
    norm2 = adapter.parse_article(art2)

    # Different articles must produce different external IDs
    assert norm1.external_id != norm2.external_id

    # Same article with different tracking parameters produces identical external ID
    art1_variant = dict(art1)
    art1_variant["url"] = (
        "https://www.thehindu.com/news/national/mumbai-rains-waterlogging-kurla/article12345.ece?utm_campaign=breaking"
    )
    norm1_variant = adapter.parse_article(art1_variant)
    assert norm1_variant.external_id == norm1.external_id


def test_gdelt_parse_article_missing_required_fields():
    """Verify NormalizationError when required url or title is missing."""
    adapter = GDELTNewsAdapter()

    # Missing URL
    art_no_url = {"title": "Test Title", "domain": "example.com"}
    with pytest.raises(NormalizationError) as exc_info:
        adapter.parse_article(art_no_url)
    assert "url" in str(exc_info.value)

    # Missing Title
    art_no_title = {"url": "https://example.com/article", "domain": "example.com"}
    with pytest.raises(NormalizationError) as exc_info:
        adapter.parse_article(art_no_title)
    assert "title" in str(exc_info.value)


@pytest.mark.asyncio
async def test_gdelt_fetch_raw_events_success():
    """Verify fetching and converting GDELT response into RawIngestionEvents."""
    mock_transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=SAMPLE_GDELT_RESPONSE)
    )
    async with httpx.AsyncClient(transport=mock_transport) as client:
        adapter = GDELTNewsAdapter(http_client=client, min_interval_seconds=0.0)
        raw_events = await adapter.fetch_raw_events(max_records=2)

    assert len(raw_events) == 2
    assert raw_events[0].source_code == "GDELT_DOC"
    assert raw_events[0].external_id is not None
    assert raw_events[0].external_id.startswith("GDELT-")


@pytest.mark.asyncio
async def test_gdelt_fetch_raw_events_empty_result():
    """Verify handling empty articles array."""
    empty_payload = {"articles": []}
    mock_transport = httpx.MockTransport(lambda request: httpx.Response(200, json=empty_payload))
    async with httpx.AsyncClient(transport=mock_transport) as client:
        adapter = GDELTNewsAdapter(http_client=client, min_interval_seconds=0.0)
        events = await adapter.fetch_raw_events()
    assert events == []


@pytest.mark.asyncio
async def test_gdelt_fetch_raw_events_http_and_timeout_errors():
    """Verify handling HTTP 404, 500, and timeout failures."""
    # HTTP 500
    mock_transport_500 = httpx.MockTransport(
        lambda request: httpx.Response(500, text="Internal Server Error")
    )
    async with httpx.AsyncClient(transport=mock_transport_500) as client:
        adapter = GDELTNewsAdapter(http_client=client, min_interval_seconds=0.0)
        with pytest.raises(AdapterFetchError) as exc_info:
            await adapter.fetch_raw_events()
        assert "500" in str(exc_info.value)

    # HTTP Timeout
    async def mock_timeout(request):
        raise httpx.ConnectTimeout("Connection timed out")

    mock_transport_timeout = httpx.MockTransport(mock_timeout)
    async with httpx.AsyncClient(transport=mock_transport_timeout) as client:
        adapter = GDELTNewsAdapter(http_client=client, min_interval_seconds=0.0)
        with pytest.raises(AdapterFetchError) as exc_info:
            await adapter.fetch_raw_events()
        assert "Network communication error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_gdelt_rate_limiting_throttle():
    """Verify adapter enforces minimum request interval throttle."""
    mock_transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"articles": []}))
    async with httpx.AsyncClient(transport=mock_transport) as client:
        # Enforce 0.2s minimum interval
        adapter = GDELTNewsAdapter(http_client=client, min_interval_seconds=0.2)
        start_time = time.monotonic()
        await adapter.fetch_raw_events()
        await adapter.fetch_raw_events()
        elapsed = time.monotonic() - start_time
        assert elapsed >= 0.18


@pytest.mark.asyncio
async def test_evidence_persistence_and_idempotency(db_session: AsyncSession):
    """Verify evidence persistence in PostgreSQL and idempotency on repeated ingestion."""
    ev_svc = EvidenceService()
    unique_suffix = uuid.uuid4().hex[:8]
    test_url = f"https://example.com/news/flood-alert-{unique_suffix}"
    url_hash = hashlib.sha256(test_url.encode("utf-8")).hexdigest()
    ext_id = f"GDELT-{url_hash}"

    event = NormalizedEvidenceEvent(
        source_code="GDELT_DOC",
        external_id=ext_id,
        evidence_type="NEWS_ARTICLE",
        title=f"Severe Flooding Alert {unique_suffix}",
        url=test_url,
        publisher_domain="example.com",
        language="English",
        published_at=datetime.now(timezone.utc),
        sha256_hash=url_hash,
        raw_payload={"sourcecountry": "India"},
    )

    # 1. First ingestion -> Creates new EvidenceItem
    ev1 = await ev_svc.ingest_normalized_evidence(db_session, event)
    assert ev1.id is not None
    assert ev1.external_id == ext_id
    assert ev1.title == f"Severe Flooding Alert {unique_suffix}"

    # 2. Second ingestion with same external_id -> Updates existing, does not duplicate
    event_updated = NormalizedEvidenceEvent(
        source_code="GDELT_DOC",
        external_id=ext_id,
        evidence_type="NEWS_ARTICLE",
        title=f"Severe Flooding Alert {unique_suffix} (Updated)",
        url=test_url,
        publisher_domain="example.com",
        language="English",
        published_at=datetime.now(timezone.utc),
        sha256_hash=url_hash,
        raw_payload={"sourcecountry": "India", "updated": True},
    )
    ev2 = await ev_svc.ingest_normalized_evidence(db_session, event_updated)
    assert ev2.id == ev1.id
    assert "Updated" in ev2.title
    assert ev2.raw_payload is not None
    assert ev2.raw_payload.get("updated") is True

    # Confirm count in database is exactly 1
    count_stmt = select(EvidenceItem).where(EvidenceItem.external_id == ext_id)
    count_res = await db_session.execute(count_stmt)
    assert len(count_res.scalars().all()) == 1


@pytest.mark.asyncio
async def test_evidence_stream_publish_and_worker_ack():
    """Verify publishing evidence to Redis Stream and consumer worker processing."""
    mock_redis = MagicMock()
    mock_redis.xadd = AsyncMock(return_value="1724930000000-0")
    mock_redis.xack = AsyncMock(return_value=1)
    mock_redis.xgroup_create = AsyncMock(return_value=True)

    stream_svc = StreamService(client=mock_redis)

    test_ev = NormalizedEvidenceEvent(
        source_code="GDELT_DOC",
        external_id="GDELT-1122334455667788",
        evidence_type="NEWS_ARTICLE",
        title="Cyclone Warning Issued for Western Coast",
        url="https://example.com/cyclone-alert",
        publisher_domain="example.com",
        published_at=datetime.now(timezone.utc),
    )

    # Publish
    msg_id = await stream_svc.publish_evidence(test_ev, stream_name="stream:weather:evidence")
    assert msg_id == "1724930000000-0"
    mock_redis.xadd.assert_called_once()

    # Ack
    ack_res = await stream_svc.ack_evidence(
        msg_id,
        stream_name="stream:weather:evidence",
        group_name="group:weather:evidence_processors",
    )
    assert ack_res is True
    mock_redis.xack.assert_called_once_with(
        "stream:weather:evidence",
        "group:weather:evidence_processors",
        "1724930000000-0",
    )


@pytest.mark.asyncio
async def test_evidence_worker_batch_consumption_and_ack():
    """Verify EvidenceWorker consuming, persisting, and acknowledging stream evidence."""
    mock_stream = MagicMock()
    mock_ev_svc = MagicMock()

    test_ev = NormalizedEvidenceEvent(
        source_code="GDELT_DOC",
        external_id="GDELT-9988776655443322",
        evidence_type="NEWS_ARTICLE",
        title="Landslide Blocks Highway in Himachal",
        url="https://example.com/landslide-news",
        publisher_domain="example.com",
        published_at=datetime.now(timezone.utc),
    )

    mock_stream.read_evidence = AsyncMock(return_value=[("3001-0", test_ev)])
    mock_stream.ack_evidence = AsyncMock(return_value=True)

    fake_evidence = MagicMock()
    fake_evidence.external_id = "GDELT-9988776655443322"
    mock_ev_svc.ingest_normalized_evidence = AsyncMock(return_value=fake_evidence)

    worker = EvidenceWorker(
        stream_svc=mock_stream,
        ev_svc=mock_ev_svc,
        consumer_name="test-ev-worker",
    )

    results = await worker.process_batch(count=1)

    assert len(results) == 1
    msg_id, ev_result = results[0]
    assert msg_id == "3001-0"
    assert ev_result is fake_evidence

    mock_stream.read_evidence.assert_called_once_with(
        consumer_name="test-ev-worker",
        count=1,
        block_ms=1000,
        from_id=">",
    )
    mock_ev_svc.ingest_normalized_evidence.assert_called_once()
    mock_stream.ack_evidence.assert_called_once_with("3001-0")


@pytest.mark.asyncio
async def test_evidence_worker_recoverable_failure_no_ack():
    """Verify EvidenceWorker does NOT ack message if persistence encounters an error."""
    mock_stream = MagicMock()
    mock_ev_svc = MagicMock()

    test_ev = NormalizedEvidenceEvent(
        source_code="GDELT_DOC",
        external_id="GDELT-FAIL-01",
        evidence_type="NEWS_ARTICLE",
        title="Failing Article",
        url="https://example.com/fail",
    )

    mock_stream.read_evidence = AsyncMock(return_value=[("3002-0", test_ev)])
    mock_stream.ack_evidence = AsyncMock(return_value=True)

    mock_ev_svc.ingest_normalized_evidence = AsyncMock(
        side_effect=RuntimeError("Database deadlock")
    )

    worker = EvidenceWorker(
        stream_svc=mock_stream,
        ev_svc=mock_ev_svc,
        consumer_name="test-ev-worker",
    )

    results = await worker.process_batch(count=1)

    assert len(results) == 1
    msg_id, ev_result = results[0]
    assert msg_id == "3002-0"
    assert ev_result is None

    # CRITICAL: Message must NOT be acknowledged so it stays in PEL
    mock_stream.ack_evidence.assert_not_called()


def test_gdelt_source_country_vs_event_location_semantics():
    """Verify Indian publisher covering foreign disaster is NOT classified as Indian incident."""
    adapter = GDELTNewsAdapter()
    foreign_event_article = {
        "url": "https://aninews.in/news/national/general-news/nepal-floods-death-toll-reaches-62620260829110355",
        "title": "Nepal floods : Death toll reaches 626 , over 4 , 400 rescued",
        "seendate": "20260829T081500Z",
        "domain": "aninews.in",
        "language": "English",
        "sourcecountry": "India",
    }

    norm = adapter.parse_article(foreign_event_article)

    # 1. sourcecountry is preserved strictly as source metadata
    assert norm.raw_payload.get("sourcecountry") == "India"

    # 2. Evidence event is strictly secondary evidence, NOT an incident
    assert norm.evidence_type == "NEWS_ARTICLE"
    assert norm.source_code == "GDELT_DOC"

    # 3. Model contains no geographic coordinates / no fabricated India bounding box
    assert not hasattr(norm, "latitude")
    assert not hasattr(norm, "longitude")


def test_gdelt_seendate_is_not_incident_occurrence_time():
    """Verify GDELT seendate is mapped to published_at/indexing time, not occurred_at."""
    adapter = GDELTNewsAdapter()
    article = {
        "url": "https://example.com/article/1",
        "title": "Heavy rains flood local lowlands",
        "seendate": "20260829T120000Z",
        "domain": "example.com",
    }

    norm = adapter.parse_article(article)

    # seendate maps to published_at
    assert norm.published_at == datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)

    # NormalizedEvidenceEvent has NO occurred_at field (distinct from NormalizedIngestionEvent)
    assert not hasattr(norm, "occurred_at")


@pytest.mark.asyncio
async def test_gdelt_evidence_stored_without_coordinates(db_session: AsyncSession):
    """Verify EvidenceItem persistence in PostgreSQL without spatial geometry columns."""
    ev_svc = EvidenceService()
    test_url = f"https://example.com/news/article-{uuid.uuid4().hex[:8]}"
    url_hash = hashlib.sha256(test_url.encode("utf-8")).hexdigest()
    ext_id = f"GDELT-{url_hash}"

    event = NormalizedEvidenceEvent(
        source_code="GDELT_DOC",
        external_id=ext_id,
        evidence_type="NEWS_ARTICLE",
        title="Unlocated News Article",
        url=test_url,
        publisher_domain="example.com",
        published_at=datetime.now(timezone.utc),
        sha256_hash=url_hash,
        raw_payload={"sourcecountry": "India"},
    )

    persisted = await ev_svc.ingest_normalized_evidence(db_session, event)
    assert persisted.id is not None
    assert persisted.external_id == ext_id

    # Confirm EvidenceItem model has no geom attribute
    assert not hasattr(persisted, "geom")
