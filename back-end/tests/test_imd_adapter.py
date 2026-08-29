from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy import delete, select

from app.db.session import async_session_factory
from app.ingestion.exceptions import AdapterFetchError
from app.ingestion.imd_adapter import IMDNowcastAdapter
from app.ingestion.registry import adapter_registry
from app.models.report import WeatherReport
from app.models.source import Source
from app.services.report_service import report_service

# ---------------------------------------------------------------------------
# Representative Synthetic IMD Response Fixtures (Matching Documented Schema)
# ---------------------------------------------------------------------------
SAMPLE_IMD_NOWCAST_RESPONSE = {
    "status": "SUCCESS",
    "data": [
        {
            "id": "NOWCAST-PUNE-20260829-01",
            "district_id": "PUNE_521",
            "district_name": "Pune",
            "state_name": "Maharashtra",
            "latitude": 18.5204,
            "longitude": 73.8567,
            "warning_type": "Thunderstorm with Heavy Rain",
            "color_code": "Orange",
            "issue_time": "2026-08-29T10:00:00Z",
            "valid_until": "2026-08-29T13:00:00Z",
            "description": "Intense spells of rain with squally winds (45-55 kmph) likely.",
            "instruction": "Avoid sheltering under trees during lightning.",
            "rainfall_mm": 48.5,
            "wind_speed_kmph": 52.0,
        },
        {
            "district_id": "MUMBAI_SUB_522",
            "district_name": "Mumbai Suburban",
            "state_name": "Maharashtra",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "warning_type": "Extremely Heavy Rainfall Warning",
            "color_code": "Red",
            "issue_time": "2026-08-29T09:30:00Z",
            "valid_until": "2026-08-29T15:30:00Z",
            "description": "Extremely heavy rainfall causing severe urban waterlogging.",
            "instruction": "Stay indoors unless in emergencies.",
            "rainfall_mm": 115.0,
        },
        {
            "district_id": "AHMEDABAD_475",
            "district_name": "Ahmedabad",
            "state_name": "Gujarat",
            "latitude": 23.0225,
            "longitude": 72.5714,
            "warning_type": "Heatwave Conditions",
            "color_code": "Yellow",
            "issue_time": "2026-08-29T08:00:00Z",
            "description": "Maximum temperature reaching 43.5C.",
            "temp_c": 43.5,
        },
    ],
}


# ---------------------------------------------------------------------------
# Unit & Functional Tests
# ---------------------------------------------------------------------------
def test_imd_adapter_registry_lookup():
    """Verify IMD adapter registration in AdapterRegistry."""
    adapter = adapter_registry.get("IMD_NOWCAST")
    assert adapter is not None
    assert isinstance(adapter, IMDNowcastAdapter)
    assert adapter.source_code == "IMD_NOWCAST"
    assert adapter.source_type == "GOVERNMENT_PORTAL"
    assert adapter.base_trust_score == 0.90


def test_imd_severity_mapping():
    """Verify deterministic mapping of IMD alert colors and text levels to 4-tier domain."""
    assert IMDNowcastAdapter.map_imd_severity("Red") == "SEVERE"
    assert IMDNowcastAdapter.map_imd_severity("red") == "SEVERE"
    assert IMDNowcastAdapter.map_imd_severity("Orange") == "HIGH"
    assert IMDNowcastAdapter.map_imd_severity("Amber") == "HIGH"
    assert IMDNowcastAdapter.map_imd_severity("Yellow") == "MODERATE"
    assert IMDNowcastAdapter.map_imd_severity("Green") == "LOW"
    assert IMDNowcastAdapter.map_imd_severity("White") == "LOW"
    assert IMDNowcastAdapter.map_imd_severity("Extreme") == "SEVERE"
    assert IMDNowcastAdapter.map_imd_severity("Heavy") == "HIGH"
    assert IMDNowcastAdapter.map_imd_severity("No Warning") == "LOW"


def test_imd_category_mapping():
    """Verify deterministic mapping of IMD hazard keywords to standard taxonomy."""
    assert (
        IMDNowcastAdapter.map_imd_category("Thunderstorm with Lightning")
        == "THUNDERSTORM_LIGHTNING"
    )
    assert IMDNowcastAdapter.map_imd_category("Heavy Rainfall Warning") == "HEAVY_RAINFALL"
    assert IMDNowcastAdapter.map_imd_category("Flash Flood Inundation") == "FLOOD_WATERLOGGING"
    assert IMDNowcastAdapter.map_imd_category("Severe Heatwave") == "HEATWAVE"
    assert IMDNowcastAdapter.map_imd_category("Hailstorm Activity") == "HAILSTORM"
    assert IMDNowcastAdapter.map_imd_category("Cyclone Gale Squall") == "CYCLONE_GALE"
    assert IMDNowcastAdapter.map_imd_category("Unknown Event") == "OTHER"


def test_imd_external_id_generation():
    """Verify stable and deterministic external_id generation."""
    # With explicit id
    rec1 = {"id": "ALERT-12345", "district_id": "PUNE_521"}
    assert IMDNowcastAdapter.generate_external_id(rec1) == "IMD-ALERT-12345"

    # Composite generation without explicit id
    rec2 = {
        "district_id": "MUMBAI_SUB",
        "issue_time": "2026-08-29T10:00:00Z",
        "warning_type": "HEAVY_RAIN",
    }
    ext_id = IMDNowcastAdapter.generate_external_id(rec2)
    assert ext_id.startswith("IMD-MUMBAI_SUB-")
    assert "HEAVY_RAIN" in ext_id


@pytest.mark.asyncio
async def test_imd_adapter_parse_and_normalization():
    """Test full parsing and normalization of synthetic IMD response."""
    adapter = IMDNowcastAdapter()
    raw_events = adapter.parse_source_response(SAMPLE_IMD_NOWCAST_RESPONSE)

    assert len(raw_events) == 3

    # Event 1: Pune
    pune_raw = raw_events[0]
    pune_norm = await adapter.normalize(pune_raw)
    assert pune_norm.source_code == "IMD_NOWCAST"
    assert pune_norm.external_id == "IMD-NOWCAST-PUNE-20260829-01"
    assert pune_norm.severity == "HIGH"
    assert pune_norm.category_code == "THUNDERSTORM_LIGHTNING"
    assert pune_norm.latitude == 18.5204
    assert pune_norm.longitude == 73.8567
    assert pune_norm.location_name == "Pune, Maharashtra"
    assert "rainfall_mm" in pune_norm.raw_payload["imd_raw_record"]

    # Event 2: Mumbai
    mumbai_raw = raw_events[1]
    mumbai_norm = await adapter.normalize(mumbai_raw)
    assert mumbai_norm.severity == "SEVERE"
    assert mumbai_norm.category_code == "HEAVY_RAINFALL"
    assert mumbai_norm.latitude == 19.0760
    assert mumbai_norm.location_name == "Mumbai Suburban, Maharashtra"


@pytest.mark.asyncio
async def test_imd_mocked_live_fetch_success():
    """Test HTTP fetching using a mocked httpx response."""
    from unittest.mock import MagicMock

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_IMD_NOWCAST_RESPONSE
    mock_response.raise_for_status.return_value = None
    mock_client.get.return_value = mock_response

    adapter = IMDNowcastAdapter(
        api_key="test_mock_key",
        custom_client=mock_client,
    )

    normalized_events = await adapter.ingest()
    assert len(normalized_events) == 3
    mock_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_imd_http_error_handling():
    """Test clean handling and categorization of HTTP 401, 429, 500, and timeout errors."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    # 401 Unauthorized
    res_401 = AsyncMock()
    res_401.status_code = 401
    res_401.text = '{"error": "API key missing"}'
    mock_client.get.return_value = res_401

    adapter = IMDNowcastAdapter(custom_client=mock_client)
    with pytest.raises(AdapterFetchError) as exc_401:
        await adapter.fetch_raw_events()
    assert "Authentication required" in str(exc_401.value)

    # 429 Rate Limit
    res_429 = AsyncMock()
    res_429.status_code = 429
    res_429.text = '{"error": "Rate limit exceeded"}'
    mock_client.get.return_value = res_429
    with pytest.raises(AdapterFetchError) as exc_429:
        await adapter.fetch_raw_events()
    assert "rate limit" in str(exc_429.value)

    # Timeout
    mock_client.get.side_effect = httpx.TimeoutException("Connection timed out")
    with pytest.raises(AdapterFetchError) as exc_to:
        await adapter.fetch_raw_events()
    assert "timeout" in str(exc_to.value).lower()


@pytest.mark.asyncio
async def test_imd_malformed_and_empty_response_handling():
    """Test handling of empty, non-dict, and malformed records from IMD response envelopes."""
    adapter = IMDNowcastAdapter()

    # 1. Empty payload
    empty_events = adapter.parse_source_response([])
    assert empty_events == []

    # 2. Empty dict / unknown envelope
    empty_dict_events = adapter.parse_source_response({})
    assert len(empty_dict_events) == 1  # Formulates fallback event with defaults

    # 3. List with malformed entries (e.g., non-dict primitives)
    mixed_data = ["not_a_dict", 12345, {"district_name": "Nagpur", "color_code": "Yellow"}]
    parsed = adapter.parse_source_response(mixed_data)
    assert len(parsed) == 1
    assert "Nagpur" in parsed[0].payload["title"]


@pytest.mark.asyncio
async def test_imd_ingestion_persistence_and_idempotency():
    """Test end-to-end persistence and idempotency with an IMD normalized event."""
    adapter = IMDNowcastAdapter()
    sample_record = {
        "id": f"TEST-IMD-PUNE-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "district_name": "Pune",
        "state_name": "Maharashtra",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "warning_type": "Severe Thunderstorm",
        "color_code": "Red",
        "issue_time": datetime.now(timezone.utc).isoformat(),
        "rainfall_mm": 62.0,
    }

    raw_event = adapter.parse_single_record(sample_record)
    norm_event = await adapter.normalize(raw_event)

    async with async_session_factory() as session:
        # First persistence run
        report1 = await report_service.ingest_normalized_event(session, norm_event)
        assert report1 is not None
        assert report1.external_id == norm_event.external_id
        assert report1.severity == "SEVERE"
        assert report1.credibility_score == 0.0  # Decoupled from source trust

        # Verify source table has base_trust_score
        src_stmt = select(Source).where(Source.id == report1.source_id)
        src_res = await session.execute(src_stmt)
        src = src_res.scalar_one()
        assert src.base_trust_score == 0.90  # Source baseline trust metadata

        # Second persistence run (Same external ID) -> Should update, not duplicate
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
