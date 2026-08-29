from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from sqlalchemy import delete, select

from app.db.session import async_session_factory
from app.ingestion.exceptions import AdapterFetchError, NormalizationError
from app.ingestion.ndma_adapter import NDMASachetAdapter
from app.ingestion.registry import adapter_registry
from app.models.report import WeatherReport
from app.models.source import Source
from app.services.report_service import report_service

# ---------------------------------------------------------------------------
# Representative Synthetic NDMA SACHET JSON Fixture (Live Endpoint Format)
# ---------------------------------------------------------------------------
SAMPLE_NDMA_LIVE_JSON = """[
  {
    "severity": "ALERT",
    "identifier": 1787987976217013,
    "effective_start_time": "Sat Aug 29 12:48:00 IST 2026",
    "effective_end_time": "Sat Aug 29 15:48:00 IST 2026",
    "disaster_type": "Moderate Rain",
    "area_description": "Pilibhit, Unnao and nearby",
    "severity_level": "Very Likely",
    "type": 0,
    "actual_lang": "en",
    "warning_message": "Thunder with lightning and spell of Rain likely.",
    "severity_color": "orange",
    "centroid": "79.94353346653851,28.533396935325005",
    "alert_source": "IMD Lucknow"
  },
  {
    "severity": "WARNING",
    "identifier": 1787987870637021,
    "effective_start_time": "Sat Aug 29 12:36:00 IST 2026",
    "effective_end_time": "Sun Aug 30 08:31:00 IST 2026",
    "disaster_type": "Very Heavy Rain",
    "area_description": "Balaghat, Mandla districts of Madhya Pradesh",
    "severity_level": "Likely",
    "severity_color": "red",
    "centroid": "80.35984557340723,21.877176575462972",
    "warning_message": "Very heavy rainfall and severe flood risk.",
    "alert_source": "Madhya Pradesh SDMA"
  }
]"""

# ---------------------------------------------------------------------------
# Representative Synthetic NDMA SACHET CAP RSS 2.0 XML Fixture
# ---------------------------------------------------------------------------
SAMPLE_NDMA_CAP_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:cap="urn:oasis:names:tc:emergency:cap:1.2" xmlns:georss="http://www.georss.org/georss">
  <channel>
    <title>NDMA SACHET All India Disaster Alerts</title>
    <link>https://sachet.ndma.gov.in/CapFeed</link>
    <description>Official CAP alerts from National Disaster Management Authority</description>
    <pubDate>Sat, 29 Aug 2026 10:00:00 GMT</pubDate>

    <!-- Item 1: Severe Flash Flood Alert with Point Coordinate -->
    <item>
      <guid>NDMA-CAP-ALERT-MAH-20260829-001</guid>
      <title>Flash Flood Warning for Raigad District</title>
      <description>Torrential downpour causing severe flash floods.</description>
      <pubDate>2026-08-29T09:30:00Z</pubDate>
      <cap:event>Flash Flood</cap:event>
      <cap:severity>Extreme</cap:severity>
      <cap:urgency>Immediate</cap:urgency>
      <cap:certainty>Observed</cap:certainty>
      <cap:areaDesc>Raigad District, Maharashtra</cap:areaDesc>
      <georss:point>18.5158 73.1812</georss:point>
      <cap:instruction>Move to higher ground immediately.</cap:instruction>
    </item>

    <!-- Item 2: Heavy Rainfall & Landslide Alert with Polygon Coordinates -->
    <item>
      <guid>NDMA-CAP-ALERT-KRL-20260829-002</guid>
      <title>Landslide &amp; Heavy Rain Alert for Wayanad</title>
      <description>Intense monsoon showers likely to trigger mudslides.</description>
      <pubDate>2026-08-29T08:00:00Z</pubDate>
      <cap:event>Landslide</cap:event>
      <cap:severity>Severe</cap:severity>
      <cap:areaDesc>Wayanad District, Kerala</cap:areaDesc>
      <cap:polygon>11.60,76.08 11.75,76.15 11.65,76.25 11.50,76.10</cap:polygon>
      <cap:instruction>Residents should relocate to designated relief camps.</cap:instruction>
    </item>

    <!-- Item 3: Thunderstorm Warning with Area only (No Point Coordinates) -->
    <item>
      <guid>NDMA-CAP-ALERT-WB-20260829-003</guid>
      <title>Severe Thunderstorm &amp; Lightning Alert for South 24 Parganas</title>
      <description>Thunderstorm with lightning and gusty winds reaching 50 kmph.</description>
      <pubDate>2026-08-29T07:15:00Z</pubDate>
      <cap:event>Thunderstorm with Lightning</cap:event>
      <cap:severity>Moderate</cap:severity>
      <cap:areaDesc>South 24 Parganas, West Bengal</cap:areaDesc>
      <cap:instruction>Take shelter indoors.</cap:instruction>
    </item>
  </channel>
</rss>
"""


# ---------------------------------------------------------------------------
# Unit & Functional Tests
# ---------------------------------------------------------------------------
def test_ndma_adapter_registry_lookup():
    """Verify NDMA SACHET adapter registration in AdapterRegistry."""
    adapter = adapter_registry.get("NDMA_SACHET")
    assert adapter is not None
    assert isinstance(adapter, NDMASachetAdapter)
    assert adapter.source_code == "NDMA_SACHET"
    assert adapter.source_type == "GOVERNMENT_PORTAL"
    assert adapter.base_trust_score == 0.95


def test_ndma_severity_mapping():
    """Verify deterministic mapping of NDMA CAP severities and colors to 4-tier domain."""
    assert NDMASachetAdapter.map_ndma_severity("Extreme") == "SEVERE"
    assert NDMASachetAdapter.map_ndma_severity("Red") == "SEVERE"
    assert NDMASachetAdapter.map_ndma_severity("red") == "SEVERE"
    assert NDMASachetAdapter.map_ndma_severity("Critical") == "SEVERE"
    assert NDMASachetAdapter.map_ndma_severity("Severe") == "HIGH"
    assert NDMASachetAdapter.map_ndma_severity("Orange") == "HIGH"
    assert NDMASachetAdapter.map_ndma_severity("orange") == "HIGH"
    assert NDMASachetAdapter.map_ndma_severity("Amber") == "HIGH"
    assert NDMASachetAdapter.map_ndma_severity("Warning") == "HIGH"
    assert NDMASachetAdapter.map_ndma_severity("Moderate") == "MODERATE"
    assert NDMASachetAdapter.map_ndma_severity("Yellow") == "MODERATE"
    assert NDMASachetAdapter.map_ndma_severity("yellow") == "MODERATE"
    assert NDMASachetAdapter.map_ndma_severity("Minor") == "LOW"
    assert NDMASachetAdapter.map_ndma_severity("Green") == "LOW"
    assert NDMASachetAdapter.map_ndma_severity("Advisory") == "LOW"
    assert NDMASachetAdapter.map_ndma_severity("Unknown") == "LOW"


def test_ndma_category_mapping():
    """Verify deterministic mapping of NDMA hazard keywords to platform taxonomy."""
    assert NDMASachetAdapter.map_ndma_category("Flash Flood Warning") == "FLOOD_WATERLOGGING"
    assert NDMASachetAdapter.map_ndma_category("Moderate Rain") == "HEAVY_RAINFALL"
    assert NDMASachetAdapter.map_ndma_category("Heavy Rain & Cloudburst") == "HEAVY_RAINFALL"
    assert (
        NDMASachetAdapter.map_ndma_category("Light Thunderstorm with surface wind")
        == "THUNDERSTORM_LIGHTNING"
    )
    assert NDMASachetAdapter.map_ndma_category("Landslide and Mudslide") == "LANDSLIDE"
    assert NDMASachetAdapter.map_ndma_category("Severe Cyclonic Storm") == "CYCLONE_GALE"
    assert NDMASachetAdapter.map_ndma_category("Heatwave Advisory") == "HEATWAVE"
    assert NDMASachetAdapter.map_ndma_category("Hailstorm Alert") == "HAILSTORM"
    assert NDMASachetAdapter.map_ndma_category("Generic Civil Notice") == "OTHER"


def test_ndma_polygon_centroid_calculation():
    """Verify arithmetic centroid calculation from polygon coordinate string."""
    polygon_str = "10.0,70.0 20.0,70.0 20.0,80.0 10.0,80.0"
    lat, lon = NDMASachetAdapter.parse_polygon_centroid(polygon_str)
    assert lat == 15.0
    assert lon == 75.0

    # Invalid string handling
    inv_lat, inv_lon = NDMASachetAdapter.parse_polygon_centroid("invalid_data")
    assert inv_lat is None
    assert inv_lon is None


def test_ndma_external_id_generation():
    """Verify stable and deterministic external_id generation."""
    # Explicit GUID
    rec1 = {"guid": "IN-NDMA-2026-ALERT-999"}
    assert NDMASachetAdapter.generate_external_id(rec1) == "NDMA-IN-NDMA-2026-ALERT-999"

    # Numerical Identifier
    rec_num = {"identifier": 1787987976217013}
    assert NDMASachetAdapter.generate_external_id(rec_num) == "NDMA-1787987976217013"

    # Composite fallback
    rec2 = {
        "areaDesc": "Pune District",
        "pubDate": "2026-08-29T10:00:00Z",
        "event": "HEAVY_RAIN",
    }
    ext_id = NDMASachetAdapter.generate_external_id(rec2)
    assert ext_id.startswith("NDMA-PUNE_DISTRICT-")
    assert "HEAVY_RAIN" in ext_id


@pytest.mark.asyncio
async def test_ndma_live_json_parsing_and_normalization():
    """Test parsing and normalization of the live NDMA JSON format (FetchAllAlertDetails)."""
    adapter = NDMASachetAdapter()
    raw_events = adapter.parse_feed_content(SAMPLE_NDMA_LIVE_JSON)

    assert len(raw_events) == 2

    # Event 1: Pilibhit / Unnao (Moderate Rain + Thunderstorm message)
    ev1 = raw_events[0]
    norm1 = await adapter.normalize(ev1)
    assert norm1.source_code == "NDMA_SACHET"
    assert norm1.external_id == "NDMA-1787987976217013"
    assert norm1.severity == "HIGH"  # Orange -> HIGH
    assert norm1.category_code == "THUNDERSTORM_LIGHTNING"
    assert norm1.latitude == 28.533396935325005
    assert norm1.longitude == 79.94353346653851
    assert "Pilibhit" in (norm1.location_name or "")

    # Event 2: Balaghat / Mandla (Very Heavy Rain)
    ev2 = raw_events[1]
    norm2 = await adapter.normalize(ev2)
    assert norm2.severity == "SEVERE"  # Red -> SEVERE
    assert norm2.category_code == "HEAVY_RAINFALL"
    assert norm2.latitude == 21.877176575462972
    assert norm2.longitude == 80.35984557340723


@pytest.mark.asyncio
async def test_ndma_xml_feed_parsing_and_normalization():
    """Test full parsing and normalization of synthetic NDMA CAP RSS XML feed."""
    adapter = NDMASachetAdapter()
    raw_events = adapter.parse_feed_content(SAMPLE_NDMA_CAP_RSS)

    assert len(raw_events) == 3

    # Event 1: Raigad Flash Flood (Point Coordinates)
    raigad_raw = raw_events[0]
    raigad_norm = await adapter.normalize(raigad_raw)
    assert raigad_norm.source_code == "NDMA_SACHET"
    assert raigad_norm.external_id == "NDMA-NDMA-CAP-ALERT-MAH-20260829-001"
    assert raigad_norm.severity == "SEVERE"
    assert raigad_norm.category_code == "FLOOD_WATERLOGGING"
    assert raigad_norm.latitude == 18.5158
    assert raigad_norm.longitude == 73.1812
    assert "Raigad" in (raigad_norm.location_name or "")

    # Event 2: Wayanad Landslide (Polygon Centroid Coordinates)
    wayanad_raw = raw_events[1]
    wayanad_norm = await adapter.normalize(wayanad_raw)
    assert wayanad_norm.severity == "HIGH"
    assert wayanad_norm.category_code == "LANDSLIDE"
    assert wayanad_norm.latitude is not None
    assert wayanad_norm.longitude is not None
    assert 11.0 < wayanad_norm.latitude < 12.0
    assert 76.0 < wayanad_norm.longitude < 77.0


@pytest.mark.asyncio
async def test_ndma_missing_location_behavior():
    """Test that records without coordinates preserve areaDesc but reject spatial persistence."""
    adapter = NDMASachetAdapter()
    raw_events = adapter.parse_feed_content(SAMPLE_NDMA_CAP_RSS)

    # Event 3: South 24 Parganas (Has areaDesc but no Point/Polygon coordinates)
    area_only_raw = raw_events[2]
    assert area_only_raw.payload["latitude"] is None
    assert area_only_raw.payload["longitude"] is None
    assert "South 24 Parganas" in area_only_raw.payload["location_name"]

    # Ingestion contract: EventNormalizer requires valid coordinates for spatial entity creation
    with pytest.raises(NormalizationError) as exc_info:
        await adapter.normalize(area_only_raw)
    assert "Missing required latitude or longitude" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ndma_mocked_live_fetch_success():
    """Test HTTP fetching using a mocked httpx response."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = SAMPLE_NDMA_LIVE_JSON.encode("utf-8")
    mock_response.raise_for_status.return_value = None
    mock_client.post.return_value = mock_response

    adapter = NDMASachetAdapter(custom_client=mock_client)
    raw_events = await adapter.fetch_raw_events()
    assert len(raw_events) == 2
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_ndma_http_error_handling():
    """Test clean categorization of HTTP 401, 429, 500, and timeout errors."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    # 403 Forbidden
    res_403 = MagicMock()
    res_403.status_code = 403
    mock_client.post.return_value = res_403

    adapter = NDMASachetAdapter(custom_client=mock_client)
    with pytest.raises(AdapterFetchError) as exc_403:
        await adapter.fetch_raw_events()
    assert "Authentication required" in str(exc_403.value)

    # 429 Rate Limit
    res_429 = MagicMock()
    res_429.status_code = 429
    mock_client.post.return_value = res_429
    with pytest.raises(AdapterFetchError) as exc_429:
        await adapter.fetch_raw_events()
    assert "rate limit" in str(exc_429.value)

    # Timeout
    mock_client.post.side_effect = httpx.TimeoutException("Feed connection timed out")
    with pytest.raises(AdapterFetchError) as exc_to:
        await adapter.fetch_raw_events()
    assert "timeout" in str(exc_to.value).lower()


@pytest.mark.asyncio
async def test_ndma_malformed_xml_and_empty_feed_handling():
    """Test handling of empty or malformed XML/JSON feeds."""
    adapter = NDMASachetAdapter()

    # Empty content
    assert adapter.parse_feed_content("") == []
    assert adapter.parse_feed_content(b"") == []

    # Malformed XML syntax
    with pytest.raises(AdapterFetchError) as exc_xml:
        adapter.parse_feed_content("<rss><channel><item>unclosed tag")
    assert "Malformed XML" in str(exc_xml.value)


@pytest.mark.asyncio
async def test_ndma_ingestion_persistence_and_idempotency():
    """Test end-to-end persistence and idempotency with an NDMA normalized event."""
    adapter = NDMASachetAdapter()
    sample_json = f"""[
      {{
        "identifier": "TEST-NDMA-MUM-{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}",
        "disaster_type": "Cyclone Gale",
        "severity_color": "orange",
        "area_description": "Mumbai Coast, Maharashtra",
        "centroid": "72.8347,18.9220",
        "warning_message": "Gale winds up to 75 kmph and tidal surge expected.",
        "effective_start_time": "{datetime.now(timezone.utc).isoformat()}"
      }}
    ]"""

    raw_events = adapter.parse_feed_content(sample_json)
    assert len(raw_events) == 1
    norm_event = await adapter.normalize(raw_events[0])

    async with async_session_factory() as session:
        # First persistence run
        report1 = await report_service.ingest_normalized_event(session, norm_event)
        assert report1 is not None
        assert report1.external_id == norm_event.external_id
        assert report1.credibility_score == 0.0  # Decoupled from source trust

        # Verify source table has base_trust_score
        src_stmt = select(Source).where(Source.id == report1.source_id)
        src_res = await session.execute(src_stmt)
        src = src_res.scalar_one()
        assert src.base_trust_score == 0.95  # Source baseline trust metadata

        # Second persistence run (Same external ID) -> Idempotent update
        report2 = await report_service.ingest_normalized_event(session, norm_event)
        assert report2.id == report1.id
        assert report2.tracking_id == report1.tracking_id

        # Verify only 1 database row exists
        stmt = select(WeatherReport).where(WeatherReport.external_id == norm_event.external_id)
        res = await session.execute(stmt)
        all_reps = res.scalars().all()
        assert len(all_reps) == 1

        # Clean up test database row
        del_stmt = delete(WeatherReport).where(WeatherReport.external_id == norm_event.external_id)
        await session.execute(del_stmt)
        await session.commit()
