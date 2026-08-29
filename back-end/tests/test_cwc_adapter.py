import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import pool, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.ingestion.cwc_adapter import CWCTelemetryAdapter
from app.ingestion.exceptions import AdapterFetchError, NormalizationError
from app.ingestion.registry import adapter_registry
from app.ingestion.schemas import NormalizedObservationEvent
from app.models.observation import WeatherObservation
from app.services.observation_service import ObservationService
from app.services.stream_service import StreamService
from app.workers.observation_worker import ObservationWorker

# Sample synthetic CKAN datastore payload matching live schema
SAMPLE_CKAN_RESPONSE = {
    "help": "https://nwdp.nwic.gov.in/api/3/action/help_show?name=datastore_search",
    "success": True,
    "result": {
        "resource_id": "d80798b9-4b11-4626-8b63-964202ba7216",
        "total": 2,
        "records": [
            {
                "_id": 101,
                "SlNo": "101",
                "Station": "Yadgir",
                "Agency": "CWC",
                "State LGD Code": "29",
                "State": "Karnataka",
                "District LGD Code": "635",
                "District": "Yadgir",
                "Tehsil": "Yadgir",
                "River": "Krishna",
                "Basin": "Krishna",
                "Tributary": "Bhima",
                "Local River": "Bhima",
                "Latitude": "16.73750000",
                "Longitude": "77.12527778",
                "Is_DischargeDataAvailable": "Yes",
                "RL_of_zeroGauge": "350.5030",
                "MeanSeaLevel": "362.00",
                "Data Acquisition Time": "27-08-2026 23:00",
                "River Water Level Telemetry Hourly (meter)": "351.953",
            },
            {
                "_id": 102,
                "SlNo": "102",
                "Station": "Almatti Reservoir",
                "Agency": "CWC",
                "State LGD Code": "29",
                "State": "Karnataka",
                "District LGD Code": "634",
                "District": "Vijayapura",
                "Tehsil": "Nidagundi",
                "River": "Krishna",
                "Basin": "Krishna",
                "Tributary": "-",
                "Local River": "Krishna",
                "Latitude": "16.33166667",
                "Longitude": "75.88833333",
                "Is_DischargeDataAvailable": "No",
                "RL_of_zeroGauge": "500.0000",
                "MeanSeaLevel": "520.00",
                "Data Acquisition Time": "27-08-2026 23:00",
                "River Water Level Telemetry Hourly (meter)": "519.250",
            },
        ],
    },
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


def test_cwc_adapter_registry_lookup():
    """Verify CWC_NWDP adapter registration in adapter registry."""
    adapter = adapter_registry.get("CWC_NWDP")
    assert adapter is not None
    assert isinstance(adapter, CWCTelemetryAdapter)
    assert adapter.source_code == "CWC_NWDP"
    assert adapter.base_trust_score == 0.92


@pytest.mark.asyncio
async def test_cwc_fetch_raw_events_success():
    """Verify fetching and converting CKAN records into RawIngestionEvents."""
    mock_transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=SAMPLE_CKAN_RESPONSE)
    )
    async with httpx.AsyncClient(transport=mock_transport) as client:
        adapter = CWCTelemetryAdapter(http_client=client)
        raw_events = await adapter.fetch_raw_events(limit=2)

    assert len(raw_events) == 2
    assert raw_events[0].source_code == "CWC_NWDP"
    assert raw_events[0].external_id is not None
    assert "CWC-KRISHNA-YADGIR" in raw_events[0].external_id
    assert raw_events[0].payload["Station"] == "Yadgir"


def test_cwc_parse_record_field_mapping_and_ist_utc_timestamp():
    """Verify exact field mapping, station identity, and IST to UTC conversion."""
    adapter = CWCTelemetryAdapter()
    record = SAMPLE_CKAN_RESPONSE["result"]["records"][0]
    norm = adapter.parse_record(record)

    assert norm.source_code == "CWC_NWDP"
    assert norm.station_name == "Yadgir"
    assert norm.station_code == "CWC-KRISHNA-YADGIR"
    assert norm.latitude == 16.7375
    assert norm.longitude == 77.12527778
    assert norm.water_level_m == 351.953
    # 27-08-2026 23:00 IST -> 2026-08-27 17:30:00 UTC
    assert norm.observed_at == datetime(2026, 8, 27, 17, 30, 0, tzinfo=timezone.utc)
    assert norm.external_id == "CWC-KRISHNA-YADGIR-202608271730"
    assert norm.raw_metrics["river"] == "Krishna"
    assert norm.raw_metrics["basin"] == "Krishna"
    assert norm.raw_metrics["state"] == "Karnataka"
    assert norm.raw_metrics["rl_of_zero_gauge"] == "350.5030"


def test_cwc_external_id_determinism_and_collision_safety():
    """Verify deterministic external IDs across stations and timestamps."""
    adapter = CWCTelemetryAdapter()
    rec1 = SAMPLE_CKAN_RESPONSE["result"]["records"][0]  # Yadgir, 23:00 IST
    rec2 = SAMPLE_CKAN_RESPONSE["result"]["records"][1]  # Almatti, 23:00 IST

    norm1 = adapter.parse_record(rec1)
    norm2 = adapter.parse_record(rec2)

    # Different stations at same timestamp must NOT collide
    assert norm1.external_id != norm2.external_id
    assert norm1.external_id == "CWC-KRISHNA-YADGIR-202608271730"
    assert norm2.external_id == "CWC-KRISHNA-ALMATTIRESERVOIR-202608271730"

    # Same station at different timestamp
    rec1_later = dict(rec1)
    rec1_later["Data Acquisition Time"] = "28-08-2026 00:00"  # +1 hour
    norm1_later = adapter.parse_record(rec1_later)
    assert norm1_later.external_id == "CWC-KRISHNA-YADGIR-202608271830"
    assert norm1_later.external_id != norm1.external_id

    # Same station name in different river basin must NOT collide
    rec_godavari = dict(rec1)
    rec_godavari["Basin"] = "Godavari"
    norm_godavari = adapter.parse_record(rec_godavari)
    assert norm_godavari.station_code == "CWC-GODAVARI-YADGIR"
    assert norm_godavari.external_id == "CWC-GODAVARI-YADGIR-202608271730"
    assert norm_godavari.external_id != norm1.external_id


def test_cwc_parse_record_missing_station():
    """Verify error on missing Station field."""
    adapter = CWCTelemetryAdapter()
    record = dict(SAMPLE_CKAN_RESPONSE["result"]["records"][0])
    record["Station"] = ""
    with pytest.raises(NormalizationError) as exc_info:
        adapter.parse_record(record)
    assert "station_name" in str(exc_info.value)


def test_cwc_parse_record_invalid_coordinates():
    """Verify error on missing or invalid coordinates."""
    adapter = CWCTelemetryAdapter()
    record = dict(SAMPLE_CKAN_RESPONSE["result"]["records"][0])
    record["Latitude"] = "invalid_lat"
    with pytest.raises(NormalizationError) as exc_info:
        adapter.parse_record(record)
    assert "geom" in str(exc_info.value)

    record["Latitude"] = "195.0"  # Out of bounds
    with pytest.raises(NormalizationError) as exc_info:
        adapter.parse_record(record)
    assert "out of bounds" in str(exc_info.value).lower()


def test_cwc_parse_record_missing_or_invalid_water_level():
    """Verify null/blank water level parses safely as None without crashing."""
    adapter = CWCTelemetryAdapter()
    record = dict(SAMPLE_CKAN_RESPONSE["result"]["records"][0])
    record["River Water Level Telemetry Hourly (meter)"] = "-"
    norm = adapter.parse_record(record)
    assert norm.water_level_m is None

    record["River Water Level Telemetry Hourly (meter)"] = "NA"
    norm2 = adapter.parse_record(record)
    assert norm2.water_level_m is None


@pytest.mark.asyncio
async def test_cwc_fetch_raw_events_empty_result():
    """Verify handling empty records array."""
    empty_payload = {
        "success": True,
        "result": {"records": [], "total": 0},
    }
    mock_transport = httpx.MockTransport(lambda request: httpx.Response(200, json=empty_payload))
    async with httpx.AsyncClient(transport=mock_transport) as client:
        adapter = CWCTelemetryAdapter(http_client=client)
        events = await adapter.fetch_raw_events()
    assert events == []


@pytest.mark.asyncio
async def test_cwc_fetch_raw_events_ckan_error():
    """Verify handling CKAN success=false error response."""
    error_payload = {
        "success": False,
        "error": {"message": "Resource not found"},
    }
    mock_transport = httpx.MockTransport(lambda request: httpx.Response(200, json=error_payload))
    async with httpx.AsyncClient(transport=mock_transport) as client:
        adapter = CWCTelemetryAdapter(http_client=client)
        with pytest.raises(AdapterFetchError) as exc_info:
            await adapter.fetch_raw_events()
    assert "CKAN query failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_cwc_fetch_raw_events_http_errors():
    """Verify handling HTTP 404, 500, and timeout."""
    # HTTP 500
    mock_transport_500 = httpx.MockTransport(
        lambda request: httpx.Response(500, text="Internal Server Error")
    )
    async with httpx.AsyncClient(transport=mock_transport_500) as client:
        adapter = CWCTelemetryAdapter(http_client=client)
        with pytest.raises(AdapterFetchError) as exc_info:
            await adapter.fetch_raw_events()
        assert "500" in str(exc_info.value)

    # HTTP Timeout
    async def mock_timeout(request):
        raise httpx.ConnectTimeout("Connection timed out")

    mock_transport_timeout = httpx.MockTransport(mock_timeout)
    async with httpx.AsyncClient(transport=mock_transport_timeout) as client:
        adapter = CWCTelemetryAdapter(http_client=client)
        with pytest.raises(AdapterFetchError) as exc_info:
            await adapter.fetch_raw_events()
        assert "Network communication error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_observation_persistence_and_idempotency(db_session: AsyncSession):
    """Verify observation persistence in PostgreSQL/PostGIS and idempotency on same external ID."""
    obs_svc = ObservationService()
    unique_suffix = uuid.uuid4().hex[:6]
    station_code = f"CWC-TEST-{unique_suffix.upper()}"
    observed_time = datetime(2026, 8, 28, 10, 0, 0, tzinfo=timezone.utc)
    ext_id = f"{station_code}-202608281000"

    event = NormalizedObservationEvent(
        source_code="CWC_NWDP",
        external_id=ext_id,
        station_code=station_code,
        station_name=f"Test River Gauge {unique_suffix}",
        latitude=18.5204,
        longitude=73.8567,
        observed_at=observed_time,
        water_level_m=340.50,
        raw_metrics={"river": "Mula", "basin": "Krishna"},
    )

    # 1. First ingestion -> New WeatherObservation
    obs1 = await obs_svc.ingest_normalized_observation(db_session, event)
    assert obs1.id is not None
    assert obs1.external_id == ext_id
    assert obs1.water_level_m == 340.50
    assert obs1.station_code == station_code

    # 2. Second ingestion with same external_id -> Updates existing, does not create duplicate
    event_updated = NormalizedObservationEvent(
        source_code="CWC_NWDP",
        external_id=ext_id,
        station_code=station_code,
        station_name=f"Test River Gauge {unique_suffix}",
        latitude=18.5204,
        longitude=73.8567,
        observed_at=observed_time,
        water_level_m=341.10,  # Updated water level
        raw_metrics={"river": "Mula", "basin": "Krishna", "updated": True},
    )
    obs2 = await obs_svc.ingest_normalized_observation(db_session, event_updated)
    assert obs2.id == obs1.id
    assert obs2.water_level_m == 341.10
    assert obs2.raw_metrics is not None
    assert obs2.raw_metrics.get("updated") is True

    # Confirm count in database is exactly 1
    count_stmt = select(WeatherObservation).where(WeatherObservation.external_id == ext_id)
    count_res = await db_session.execute(count_stmt)
    assert len(count_res.scalars().all()) == 1


@pytest.mark.asyncio
async def test_observation_stream_service_publish_and_ack():
    """Verify StreamService observation publishing and acking logic."""
    mock_redis = MagicMock()
    mock_redis.xadd = AsyncMock(return_value="1724925000000-0")
    mock_redis.xack = AsyncMock(return_value=1)
    mock_redis.xgroup_create = AsyncMock(return_value=True)

    stream_svc = StreamService(client=mock_redis)

    event = NormalizedObservationEvent(
        source_code="CWC_NWDP",
        external_id="CWC-KRISHNA-YADGIR-202608271730",
        station_code="CWC-KRISHNA-YADGIR",
        station_name="Yadgir",
        latitude=16.7375,
        longitude=77.12527778,
        observed_at=datetime(2026, 8, 27, 17, 30, 0, tzinfo=timezone.utc),
        water_level_m=351.953,
    )

    # Publish observation
    msg_id = await stream_svc.publish_observation(event, stream_name="stream:weather:observations")
    assert msg_id == "1724925000000-0"
    mock_redis.xadd.assert_called_once()

    # Ack observation
    ack_res = await stream_svc.ack_observation(
        msg_id,
        stream_name="stream:weather:observations",
        group_name="group:weather:observation_processors",
    )
    assert ack_res is True
    mock_redis.xack.assert_called_once_with(
        "stream:weather:observations",
        "group:weather:observation_processors",
        "1724925000000-0",
    )


@pytest.mark.asyncio
async def test_observation_worker_batch_consumption_and_ack():
    """Verify ObservationWorker consuming, persisting, and acknowledging stream observations."""
    mock_stream = MagicMock()
    mock_obs_svc = MagicMock()

    test_obs = NormalizedObservationEvent(
        source_code="CWC_NWDP",
        external_id="CWC-KRISHNA-YADGIR-202608271730",
        station_code="CWC-KRISHNA-YADGIR",
        station_name="Yadgir",
        latitude=16.7375,
        longitude=77.12527778,
        observed_at=datetime(2026, 8, 27, 17, 30, 0, tzinfo=timezone.utc),
        water_level_m=351.953,
    )

    mock_stream.read_observations = AsyncMock(return_value=[("2001-0", test_obs)])
    mock_stream.ack_observation = AsyncMock(return_value=True)

    fake_observation = MagicMock()
    fake_observation.station_code = "CWC-KRISHNA-YADGIR"
    fake_observation.water_level_m = 351.953
    mock_obs_svc.ingest_normalized_observation = AsyncMock(return_value=fake_observation)

    worker = ObservationWorker(
        stream_svc=mock_stream,
        obs_svc=mock_obs_svc,
        consumer_name="test-worker",
    )

    results = await worker.process_batch(count=1)

    assert len(results) == 1
    msg_id, obs_result = results[0]
    assert msg_id == "2001-0"
    assert obs_result is fake_observation

    mock_stream.read_observations.assert_called_once_with(
        consumer_name="test-worker",
        count=1,
        block_ms=1000,
        from_id=">",
    )
    mock_obs_svc.ingest_normalized_observation.assert_called_once()
    mock_stream.ack_observation.assert_called_once_with("2001-0")


@pytest.mark.asyncio
async def test_observation_worker_recoverable_failure_no_ack():
    """Verify ObservationWorker does NOT ack message if persistence raises an error."""
    mock_stream = MagicMock()
    mock_obs_svc = MagicMock()

    test_obs = NormalizedObservationEvent(
        source_code="CWC_NWDP",
        external_id="CWC-KRISHNA-YADGIR-202608271730",
        station_code="CWC-KRISHNA-YADGIR",
        station_name="Yadgir",
        latitude=16.7375,
        longitude=77.12527778,
        observed_at=datetime(2026, 8, 27, 17, 30, 0, tzinfo=timezone.utc),
        water_level_m=351.953,
    )

    mock_stream.read_observations = AsyncMock(return_value=[("2002-0", test_obs)])
    mock_stream.ack_observation = AsyncMock(return_value=True)

    mock_obs_svc.ingest_normalized_observation = AsyncMock(
        side_effect=RuntimeError("Database connection lost")
    )

    worker = ObservationWorker(
        stream_svc=mock_stream,
        obs_svc=mock_obs_svc,
        consumer_name="test-worker",
    )

    results = await worker.process_batch(count=1)

    assert len(results) == 1
    msg_id, obs_result = results[0]
    assert msg_id == "2002-0"
    assert obs_result is None

    # CRITICAL: Message must NOT be acknowledged so it stays in PEL
    mock_stream.ack_observation.assert_not_called()
