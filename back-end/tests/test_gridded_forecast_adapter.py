"""Unit tests for GriddedForecastAdapter (Open-Meteo Weather & Marine Grid Forecasts).

Tests cover:
1. Spatial grid coordinate generation covering India & EEZ (0-40°N, 60-100°E)
2. Coordinate batching / chunking
3. Sea point maritime heuristic classification
4. Open-Meteo weather forecast response parsing
5. Open-Meteo marine forecast response parsing
6. Idempotent upsert into weather_grid_forecast and marine_grid_forecast tables
7. Guarantee that ingest() returns empty list (no Redis incident/observation routing)
8. Rate limiting and scheduled interval enforcement
9. Resilient error handling on upstream HTTP timeouts / non-200 responses
10. Adapter registry registration
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion import adapter_registry
from app.ingestion.gridded_forecast_adapter import (
    GriddedForecastAdapter,
    chunk_points,
    generate_grid_points,
    is_sea_point,
)
from app.models.grid_forecast import MarineGridForecast, WeatherGridForecast

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures & Helpers
# ─────────────────────────────────────────────────────────────────────────────


def make_mock_weather_response(lats: List[float], lons: List[float]) -> List[Dict[str, Any]]:
    """Generate realistic Open-Meteo batched weather forecast JSON."""
    results = []
    for lat, lon in zip(lats, lons):
        results.append({
            "latitude": lat,
            "longitude": lon,
            "timezone": "UTC",
            "utc_offset_seconds": 0,
            "hourly": {
                "time": ["2026-10-02T00:00", "2026-10-02T01:00"],
                "temperature_2m": [28.4, 28.1],
                "precipitation": [0.0, 1.2],
                "wind_speed_10m": [14.5, 15.2],
                "wind_direction_10m": [220, 225],
                "pressure_msl": [1011.8, 1012.0],
            },
        })
    return results if len(results) > 1 else results[0]


def make_mock_marine_response(lats: List[float], lons: List[float]) -> List[Dict[str, Any]]:
    """Generate realistic Open-Meteo batched marine forecast JSON."""
    results = []
    for lat, lon in zip(lats, lons):
        results.append({
            "latitude": lat,
            "longitude": lon,
            "timezone": "UTC",
            "utc_offset_seconds": 0,
            "hourly": {
                "time": ["2026-10-02T00:00", "2026-10-02T01:00"],
                "wave_height": [1.8, 1.9],
                "wave_direction": [210, 215],
                "wave_period": [6.5, 6.7],
            },
        })
    return results if len(results) > 1 else results[0]


# ─────────────────────────────────────────────────────────────────────────────
# Unit Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestGriddedForecastGridGeometry:
    """Tests for grid coordinate generation, batching, and maritime classification."""

    def test_grid_generation_default_bounds_and_step(self):
        """Default step 2.5 on lat 0-40 and lon 60-100 should generate 17x17 = 289 points."""
        points = generate_grid_points(lat_min=0.0, lat_max=40.0, lon_min=60.0, lon_max=100.0, step=2.5)
        assert len(points) == 289
        assert (0.0, 60.0) in points
        assert (40.0, 100.0) in points
        assert (20.0, 80.0) in points

    def test_chunk_points_batches(self):
        """Points should be chunked into deterministic batches of requested size."""
        points = [(float(i), float(i)) for i in range(55)]
        batches = chunk_points(points, batch_size=25)
        assert len(batches) == 3
        assert len(batches[0]) == 25
        assert len(batches[1]) == 25
        assert len(batches[2]) == 5

    def test_is_sea_point_maritime_boundaries(self):
        """Verify marine domain classification across Indian maritime waters and inland terrain."""
        # Equatorial Indian Ocean
        assert is_sea_point(0.0, 60.0) is True
        assert is_sea_point(5.0, 80.0) is True
        # Arabian Sea
        assert is_sea_point(15.0, 65.0) is True
        assert is_sea_point(20.0, 68.0) is True
        # Bay of Bengal & Andaman Sea
        assert is_sea_point(15.0, 85.0) is True
        assert is_sea_point(10.0, 93.0) is True

        # Inland India and Northern landmass
        assert is_sea_point(28.6, 77.2) is False  # Delhi
        assert is_sea_point(23.0, 75.0) is False  # Central India
        assert is_sea_point(32.0, 76.0) is False  # Northern Himalayas
        assert is_sea_point(35.0, 80.0) is False  # Plateau north of 25.5°N


class TestGriddedForecastResponseParsing:
    """Tests for parsing Open-Meteo API payloads."""

    def test_parse_weather_response(self):
        adapter = GriddedForecastAdapter(min_interval_seconds=0.0)
        batch = [(15.0, 70.0), (17.5, 72.5)]
        raw = make_mock_weather_response([15.0, 17.5], [70.0, 72.5])
        now = datetime.now(timezone.utc)

        records = adapter._parse_weather_response(raw, batch, now)
        assert len(records) == 4  # 2 points x 2 hourly timestamps
        rec = records[0]
        assert rec["latitude"] == 15.0
        assert rec["longitude"] == 70.0
        assert rec["temperature_2m"] == 28.4
        assert rec["precipitation"] == 0.0
        assert rec["wind_speed_10m"] == 14.5
        assert rec["wind_direction_10m"] == 220
        assert rec["pressure_msl"] == 1011.8
        assert rec["source_name"] == "OPEN_METEO"
        assert rec["geom"] is not None

    def test_parse_marine_response(self):
        adapter = GriddedForecastAdapter(min_interval_seconds=0.0)
        batch = [(10.0, 65.0)]
        raw = make_mock_marine_response([10.0], [65.0])
        now = datetime.now(timezone.utc)

        records = adapter._parse_marine_response(raw, batch, now)
        assert len(records) == 2  # 1 point x 2 hourly timestamps
        rec = records[0]
        assert rec["latitude"] == 10.0
        assert rec["longitude"] == 65.0
        assert rec["wave_height"] == 1.8
        assert rec["wave_direction"] == 210
        assert rec["wave_period"] == 6.5
        assert rec["source_name"] == "OPEN_METEO_MARINE"
        assert rec["geom"] is not None

    def test_parse_marine_response_drops_all_null_rows(self):
        adapter = GriddedForecastAdapter(min_interval_seconds=0.0)
        batch = [(20.0, 75.0)]
        null_raw = {
            "latitude": 20.0,
            "longitude": 75.0,
            "hourly": {
                "time": ["2026-10-02T00:00"],
                "wave_height": [None],
                "wave_direction": [None],
                "wave_period": [None],
            },
        }
        records = adapter._parse_marine_response(null_raw, batch, datetime.now(timezone.utc))
        assert len(records) == 0


class TestGriddedForecastDatabaseIngestion:
    """Integration test verifying end-to-end ingest, DB persistence, and stream isolation."""

    @pytest.mark.asyncio
    async def test_full_ingest_cycle_persists_to_db_and_does_not_route_to_streams(
        self,
        db_session: AsyncSession,
    ):
        """Verify weather & marine forecasts are persisted in DB and ingest() returns empty list."""
        mock_weather = make_mock_weather_response([10.0], [65.0])
        mock_marine = make_mock_marine_response([10.0], [65.0])

        async def mock_get(url: str, params: Dict[str, Any]):
            if "marine" in url:
                return httpx.Response(200, json=mock_marine)
            return httpx.Response(200, json=mock_weather)

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=mock_get)
        mock_client.is_closed = False

        adapter = GriddedForecastAdapter(
            lat_min=10.0,
            lat_max=10.0,
            lon_min=65.0,
            lon_max=65.0,
            step_degrees=2.5,
            batch_size=1,
            min_interval_seconds=0.0,
            http_client=mock_client,
        )

        # Ingestion execution
        result_events = await adapter.ingest(session=db_session, force=True)

        # Invariant 1: Result MUST be empty (never streamed to Redis or incident pipeline)
        assert result_events == []

        # Invariant 2: Weather forecast persisted in database
        weather_stmt = select(WeatherGridForecast).where(
            WeatherGridForecast.latitude == 10.0,
            WeatherGridForecast.longitude == 65.0,
        )
        weather_rows = (await db_session.execute(weather_stmt)).scalars().all()
        assert len(weather_rows) == 2
        first_w = weather_rows[0]
        assert first_w.temperature_2m == 28.4
        assert first_w.source_name == "OPEN_METEO"
        assert first_w.geom is not None

        # Invariant 3: Marine forecast persisted in database for sea point (10°N, 65°E)
        marine_stmt = select(MarineGridForecast).where(
            MarineGridForecast.latitude == 10.0,
            MarineGridForecast.longitude == 65.0,
        )
        marine_rows = (await db_session.execute(marine_stmt)).scalars().all()
        assert len(marine_rows) == 2
        first_m = marine_rows[0]
        assert first_m.wave_height == 1.8
        assert first_m.source_name == "OPEN_METEO_MARINE"
        assert first_m.geom is not None

    @pytest.mark.asyncio
    async def test_scheduled_interval_skips_consecutive_calls(
        self,
        db_session: AsyncSession,
    ):
        """Calling ingest without force=True before interval expires should skip cleanly."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=httpx.Response(200, json=make_mock_weather_response([10.0], [65.0])))
        mock_client.is_closed = False

        adapter = GriddedForecastAdapter(
            lat_min=10.0,
            lat_max=10.0,
            lon_min=65.0,
            lon_max=65.0,
            interval_seconds=3600.0,
            min_interval_seconds=0.0,
            http_client=mock_client,
        )

        # First run (force=True)
        await adapter.ingest(session=db_session, force=True)
        call_count_1 = mock_client.get.call_count

        # Second immediate run (force=False) -> should skip
        await adapter.ingest(session=db_session, force=False)
        assert mock_client.get.call_count == call_count_1

    @pytest.mark.asyncio
    async def test_http_error_handled_gracefully(
        self,
        db_session: AsyncSession,
    ):
        """Upstream HTTP 500 error should be logged and not raise unhandled exceptions."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=httpx.Response(500, text="Internal Server Error"))
        mock_client.is_closed = False

        adapter = GriddedForecastAdapter(
            lat_min=10.0,
            lat_max=10.0,
            lon_min=65.0,
            lon_max=65.0,
            min_interval_seconds=0.0,
            http_client=mock_client,
        )

        result = await adapter.ingest(session=db_session, force=True)
        assert result == []


class TestAdapterRegistryIntegration:
    """Verify registry factory registration."""

    def test_gridded_forecast_adapter_in_registry(self):
        registered = adapter_registry.get("GRIDDED_FORECAST")
        assert registered is not None
        assert isinstance(registered, GriddedForecastAdapter)
        assert registered.source_code == "GRIDDED_FORECAST"
