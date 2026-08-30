"""Unit and integration tests for Server-Sent Events (SSE) realtime transport endpoint.

Validates SSE framing, Last-Event-ID replay, resync semantics, heartbeats,
privacy guarantees, error resilience, and multi-client independence.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request
from httpx import ASGITransport, AsyncClient

from app.api.v1.events import (
    _format_sse_chunk,
    _format_sse_heartbeat,
    _is_stream_id_older,
    _parse_stream_event_to_envelope,
    get_redis_client,
    realtime_event_generator,
)
from app.core.redis import AsyncRedisClient
from app.main import app as main_app

# ============================================================================
# 1. Framing & Parser Unit Tests
# ============================================================================


def test_sse_chunk_framing():
    """Verify _format_sse_chunk produces strict standard SSE protocol format."""
    chunk = _format_sse_chunk(
        event_type="report.created",
        data={"event_id": "123", "test": "val"},
        event_id="1725000000000-0",
    )
    expected = (
        'id: 1725000000000-0\nevent: report.created\ndata: {"event_id":"123","test":"val"}\n\n'
    )
    assert chunk == expected


def test_sse_heartbeat_framing():
    """Verify _format_sse_heartbeat emits standard SSE comment ping."""
    hb = _format_sse_heartbeat()
    assert hb == ": ping\n\n"


def test_stream_id_older_comparison():
    """Verify stream ID ordering comparison."""
    assert _is_stream_id_older("1725000000000-0", "1725000000001-0") is True
    assert _is_stream_id_older("1725000000001-0", "1725000000001-1") is True
    assert _is_stream_id_older("1725000000001-0", "1725000000000-0") is False
    assert _is_stream_id_older("1725000000000-0", "1725000000000-0") is False


def test_parse_stream_event_to_envelope_valid():
    """Verify parsing valid stream fields into canonical RealtimeEvent dictionary."""
    fields = {
        "event_id": str(uuid.uuid4()),
        "event_type": "report.created",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "entity_id": "rep-123",
        "tracking_id": "RPT-2026-TEST",
        "payload": json.dumps({"category_code": "FLOOD_WATERLOGGING", "severity": "HIGH"}),
    }

    envelope = _parse_stream_event_to_envelope(fields)
    assert envelope is not None
    assert envelope["event_type"] == "report.created"
    assert envelope["tracking_id"] == "RPT-2026-TEST"
    assert envelope["payload"]["category_code"] == "FLOOD_WATERLOGGING"


def test_parse_stream_event_to_envelope_malformed_returns_none():
    """Verify corrupted or invalid stream fields are safely rejected without throwing."""
    # Invalid event_type
    bad_fields = {
        "event_id": "invalid-uuid",
        "event_type": "unknown.unsupported.event",
    }
    assert _parse_stream_event_to_envelope(bad_fields) is None


# ============================================================================
# 2. Generator Logic & Lifecycle Tests
# ============================================================================


@pytest.mark.asyncio
async def test_generator_streams_replay_and_live_events():
    """Verify generator yields replay events (excluding last_event_id) then transitions to live."""
    mock_redis = MagicMock(spec=AsyncRedisClient)
    mock_redis.connect = AsyncMock()
    mock_redis.close = AsyncMock()

    # Stream state: oldest is 100-0
    mock_redis.xrange = AsyncMock()
    mock_redis.xrevrange = AsyncMock(return_value=[("102-0", {})])

    # Replay query from Last-Event-ID "100-0"
    event_100 = {
        "event_id": str(uuid.uuid4()),
        "event_type": "report.created",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "entity_id": "rep-100",
        "payload": json.dumps({"category_code": "HEAVY_RAINFALL"}),
    }
    event_101 = {
        "event_id": str(uuid.uuid4()),
        "event_type": "report.verification_changed",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "entity_id": "rep-101",
        "payload": json.dumps({"previous_status": "PENDING", "new_status": "VERIFIED"}),
    }

    # Range call 1 (oldest check): returns [("100-0", ...)]
    # Range call 2 (replay): returns [("100-0", ...), ("101-0", ...)]
    mock_redis.xrange.side_effect = [
        [("100-0", event_100)],
        [("100-0", event_100), ("101-0", event_101)],
    ]

    # Live read yields 1 live event then stops
    event_102 = {
        "event_id": str(uuid.uuid4()),
        "event_type": "report.intelligence_ready",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "entity_id": "rep-102",
        "payload": json.dumps({"credibility_score": 0.9}),
    }

    mock_redis.xread = AsyncMock(
        side_effect=[
            [("stream:weather:realtime", [("102-0", event_102)])],
            [],
        ]
    )

    mock_request = MagicMock(spec=Request)
    # Disconnect after 2 cycles
    disconnect_results = [False, False, True]
    mock_request.is_disconnected = AsyncMock(side_effect=lambda: disconnect_results.pop(0))

    chunks: List[str] = []
    async for chunk in realtime_event_generator(
        request=mock_request,
        last_event_id="100-0",
        client=mock_redis,
        poll_interval=0.01,
    ):
        chunks.append(chunk)

    # 1. Replay should contain event 101-0, but NOT 100-0 (since 100-0 was last_event_id)
    assert len(chunks) == 2
    assert "id: 101-0" in chunks[0]
    assert "event: report.verification_changed" in chunks[0]

    # 2. Live stream should contain event 102-0
    assert "id: 102-0" in chunks[1]
    assert "event: report.intelligence_ready" in chunks[1]

    # Ensure Redis was closed
    mock_redis.close.assert_called_once()


@pytest.mark.asyncio
async def test_generator_emits_resync_required_when_history_trimmed():
    """Verify generator emits system.resync_required if ID is older than stream history."""
    mock_redis = MagicMock(spec=AsyncRedisClient)
    mock_redis.connect = AsyncMock()
    mock_redis.close = AsyncMock()

    # Stream state: oldest retained entry is 500-0, but client requested 100-0
    mock_redis.xrange = AsyncMock(
        side_effect=[
            [("500-0", {})],  # Oldest check
            [],  # Replay from 500-0
        ]
    )
    mock_redis.xrevrange = AsyncMock(return_value=[("500-0", {})])
    mock_redis.xread = AsyncMock(return_value=[])

    mock_request = MagicMock(spec=Request)
    mock_request.is_disconnected = AsyncMock(side_effect=[False, True])

    chunks: List[str] = []
    async for chunk in realtime_event_generator(
        request=mock_request,
        last_event_id="100-0",
        client=mock_redis,
        poll_interval=0.01,
    ):
        chunks.append(chunk)

    assert len(chunks) == 1
    assert "event: system.resync_required" in chunks[0]
    assert "RESYNC_REQUIRED" in chunks[0]
    assert "Stream history pruned" in chunks[0]


@pytest.mark.asyncio
async def test_generator_emits_heartbeat_on_idle():
    """Verify generator emits SSE comment heartbeat when stream has no events."""
    mock_redis = MagicMock(spec=AsyncRedisClient)
    mock_redis.connect = AsyncMock()
    mock_redis.close = AsyncMock()
    mock_redis.xrevrange = AsyncMock(return_value=[("100-0", {})])
    mock_redis.xread = AsyncMock(return_value=[])

    mock_request = MagicMock(spec=Request)
    # Run 3 iterations then disconnect
    iterations = [False, False, False, True]
    mock_request.is_disconnected = AsyncMock(side_effect=lambda: iterations.pop(0))

    chunks: List[str] = []
    async for chunk in realtime_event_generator(
        request=mock_request,
        last_event_id=None,
        client=mock_redis,
        heartbeat_interval=0.01,  # Short heartbeat interval for test
        poll_interval=0.01,
    ):
        chunks.append(chunk)

    assert any(c == ": ping\n\n" for c in chunks)


@pytest.mark.asyncio
async def test_generator_handles_redis_error_gracefully():
    """Verify Redis transport failure cleanly terminates stream without unhandled exceptions."""
    mock_redis = MagicMock(spec=AsyncRedisClient)
    mock_redis.connect = AsyncMock()
    mock_redis.close = AsyncMock()
    mock_redis.xrevrange = AsyncMock(return_value=[("100-0", {})])
    mock_redis.xread = AsyncMock(side_effect=ConnectionError("Redis down"))

    mock_request = MagicMock(spec=Request)
    mock_request.is_disconnected = AsyncMock(return_value=False)

    chunks: List[str] = []
    # Should not raise exception
    async for chunk in realtime_event_generator(
        request=mock_request,
        client=mock_redis,
        poll_interval=0.01,
    ):
        chunks.append(chunk)

    assert chunks == []
    mock_redis.close.assert_called_once()


# ============================================================================
# 3. HTTP Endpoint Integration & Router Tests
# ============================================================================


@pytest.mark.asyncio
async def test_sse_endpoint_headers_and_status():
    """Verify GET /api/v1/events/stream returns 200 and text/event-stream headers."""
    mock_redis = MagicMock(spec=AsyncRedisClient)
    mock_redis.connect = AsyncMock()
    mock_redis.close = AsyncMock()
    mock_redis.xrevrange = AsyncMock(return_value=[("0-0", {})])
    sample_event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "report.created",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "entity_id": "rep-test",
        "tracking_id": "RPT-TEST",
        "payload": json.dumps({"category_code": "HEAVY_RAINFALL", "severity": "LOW"}),
    }
    mock_redis.xrange = AsyncMock(
        side_effect=[
            [("0-0", {})],
            [("0-0", {}), ("0-1", sample_event)],
        ]
    )
    mock_redis.xread = AsyncMock(side_effect=ConnectionError("client test exit"))

    main_app.dependency_overrides[get_redis_client] = lambda: mock_redis
    try:
        transport = ASGITransport(app=main_app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            async with client.stream(
                "GET", "/api/v1/events/stream", headers={"Last-Event-ID": "0-0"}
            ) as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers["content-type"]
                assert "no-cache" in response.headers["cache-control"]
                assert "X-Accel-Buffering" in response.headers
                content_lines = []
                async for line in response.aiter_lines():
                    content_lines.append(line)
                assert any("id: 0-1" in item for item in content_lines)
                assert any("event: report.created" in item for item in content_lines)
    finally:
        main_app.dependency_overrides.pop(get_redis_client, None)


@pytest.mark.asyncio
async def test_api_v1_router_has_events_endpoint():
    """Verify /events route is properly registered in application OpenAPI paths."""
    openapi_schema = main_app.openapi()
    paths = openapi_schema.get("paths", {})
    assert "/api/v1/events/stream" in paths


@pytest.mark.asyncio
async def test_sse_privacy_no_sensitive_fields_in_payload():
    """Verify payloads emitted over SSE never include phone numbers or private data."""
    mock_redis = MagicMock(spec=AsyncRedisClient)
    mock_redis.connect = AsyncMock()
    mock_redis.close = AsyncMock()
    mock_redis.xrevrange = AsyncMock(return_value=[("10-0", {})])

    sample_event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "report.created",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "entity_id": "rep-sec-1",
        "tracking_id": "RPT-SEC-001",
        "payload": json.dumps(
            {
                "tracking_id": "RPT-SEC-001",
                "category_code": "HEATWAVE",
                "severity": "MODERATE",
                "verification_status": "PENDING",
                "location_name": "Worli",
                "latitude": 19.01,
                "longitude": 72.81,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "has_media": False,
            }
        ),
    }

    mock_redis.xread = AsyncMock(
        side_effect=[
            [("stream:weather:realtime", [("11-0", sample_event)])],
            [],
        ]
    )

    mock_request = MagicMock(spec=Request)
    mock_request.is_disconnected = AsyncMock(side_effect=[False, True])

    chunks: List[str] = []
    async for chunk in realtime_event_generator(
        request=mock_request,
        client=mock_redis,
        poll_interval=0.01,
    ):
        chunks.append(chunk)

    assert len(chunks) == 1
    raw_chunk = chunks[0]
    assert "phone" not in raw_chunk
    assert "password" not in raw_chunk
    assert "notes" not in raw_chunk
    assert "token" not in raw_chunk


@pytest.mark.asyncio
async def test_multiple_sse_connections_are_independent():
    """Verify multiple independent SSE generator instances stream independently."""
    sample_payload = json.dumps({"test": "data"})
    event_dict = {
        "event_id": str(uuid.uuid4()),
        "event_type": "report.created",
        "payload": sample_payload,
    }

    redis1 = MagicMock(spec=AsyncRedisClient)
    redis1.connect = AsyncMock()
    redis1.close = AsyncMock()
    redis1.xrevrange = AsyncMock(return_value=[("1-0", {})])
    redis1.xread = AsyncMock(
        side_effect=[
            [("stream:weather:realtime", [("2-0", event_dict)])],
            [],
        ]
    )

    redis2 = MagicMock(spec=AsyncRedisClient)
    redis2.connect = AsyncMock()
    redis2.close = AsyncMock()
    redis2.xrevrange = AsyncMock(return_value=[("1-0", {})])
    redis2.xread = AsyncMock(
        side_effect=[
            [("stream:weather:realtime", [("2-0", event_dict)])],
            [],
        ]
    )

    req1 = MagicMock(spec=Request)
    req1.is_disconnected = AsyncMock(side_effect=[False, True])
    req2 = MagicMock(spec=Request)
    req2.is_disconnected = AsyncMock(side_effect=[False, True])

    results1: List[str] = []
    results2: List[str] = []

    async def run_client(gen, store):
        async for c in gen:
            store.append(c)

    gen1 = realtime_event_generator(request=req1, client=redis1, poll_interval=0.01)
    gen2 = realtime_event_generator(request=req2, client=redis2, poll_interval=0.01)

    await asyncio.gather(
        run_client(gen1, results1),
        run_client(gen2, results2),
    )

    assert len(results1) == 1
    assert len(results2) == 1
    assert "id: 2-0" in results1[0]
    assert "id: 2-0" in results2[0]


@pytest.mark.asyncio
async def test_generator_replays_over_100_events_seamlessly_without_loss_or_duplicates():
    """Verify stream with >100 events replays initial 100 batch and picks up rest via live read."""
    mock_redis = MagicMock(spec=AsyncRedisClient)
    mock_redis.connect = AsyncMock()
    mock_redis.close = AsyncMock()

    # Total 120 events: 101-0 through 220-0
    total_events = 120
    all_events: List[Tuple[str, Dict[str, str]]] = []
    for i in range(1, total_events + 1):
        msg_id = f"{100 + i}-0"
        fields = {
            "event_id": str(uuid.uuid4()),
            "event_type": "report.created",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "entity_id": f"rep-{i}",
            "tracking_id": f"RPT-BATCH-{i:03d}",
            "payload": json.dumps({"index": i}),
        }
        all_events.append((msg_id, fields))

    # Oldest in stream is 100-0
    oldest_entry = ("100-0", {})
    # Replay batch of 100 entries: 100-0 (the last_id) + first 100 new entries (101-0 to 200-0)
    replay_batch = [oldest_entry] + all_events[:100]
    # Remaining 20 entries: 201-0 to 220-0
    remaining_events = all_events[100:]

    mock_redis.xrange = AsyncMock(
        side_effect=[
            [oldest_entry],  # 1. Oldest check
            replay_batch,  # 2. Replay batch of 100 items (101-0 to 200-0)
        ]
    )
    mock_redis.xrevrange = AsyncMock(return_value=[all_events[-1]])

    # Live read returns remaining 20 items on first cycle, then empty
    mock_redis.xread = AsyncMock(
        side_effect=[
            [("stream:weather:realtime", remaining_events)],
            [],
        ]
    )

    mock_request = MagicMock(spec=Request)
    # 2 cycles then disconnect
    disconnect_signals = [False, False, True]
    mock_request.is_disconnected = AsyncMock(side_effect=lambda: disconnect_signals.pop(0))

    chunks: List[str] = []
    async for chunk in realtime_event_generator(
        request=mock_request,
        last_event_id="100-0",
        client=mock_redis,
        poll_interval=0.01,
    ):
        chunks.append(chunk)

    # Must receive exactly 120 events (100 from replay + 20 from live)
    assert len(chunks) == 120

    # Verify no chunk carries "id: 100-0" (Last-Event-ID itself is skipped)
    assert not any("id: 100-0\n" in c for c in chunks)

    # Verify first, boundary, and last IDs
    assert "id: 101-0\n" in chunks[0]
    assert "id: 200-0\n" in chunks[99]
    assert "id: 201-0\n" in chunks[100]
    assert "id: 220-0\n" in chunks[119]

    # Verify all 120 event IDs are unique (zero duplicates)
    extracted_ids = [c.split("\n")[0].replace("id: ", "") for c in chunks]
    assert len(set(extracted_ids)) == 120
    assert extracted_ids == [f"{100 + i}-0" for i in range(1, 121)]


@pytest.mark.asyncio
async def test_sse_endpoint_handles_malformed_last_event_id_safely():
    """Verify HTTP endpoint handles malformed Last-Event-ID safely by emitting resync event."""
    mock_redis = MagicMock(spec=AsyncRedisClient)
    mock_redis.connect = AsyncMock()
    mock_redis.close = AsyncMock()
    mock_redis.xrevrange = AsyncMock(return_value=[("50-0", {})])
    mock_redis.xrange = AsyncMock(
        side_effect=[
            [("50-0", {})],  # 1. Oldest check (oldest is 50-0)
            [],  # 2. Replay from 50-0
        ]
    )
    mock_redis.xread = AsyncMock(side_effect=ConnectionError("client test exit"))

    main_app.dependency_overrides[get_redis_client] = lambda: mock_redis
    try:
        transport = ASGITransport(app=main_app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            async with client.stream(
                "GET",
                "/api/v1/events/stream",
                headers={"Last-Event-ID": "invalid-garbage-id"},
            ) as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers["content-type"]
                content_lines = []
                async for line in response.aiter_lines():
                    content_lines.append(line)

                # Should receive system.resync_required event
                assert any("event: system.resync_required" in line for line in content_lines)
                assert any("RESYNC_REQUIRED" in line for line in content_lines)
                assert any("invalid-garbage-id" in line for line in content_lines)
    finally:
        main_app.dependency_overrides.pop(get_redis_client, None)
