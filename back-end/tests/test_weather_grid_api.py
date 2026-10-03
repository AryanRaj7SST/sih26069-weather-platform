"""API integration tests for /api/v1/weather endpoints (Grid, Marine Grid, Nearest Point).

Tests cover:
- GET /api/v1/weather/grid GeoJSON output and bbox filtering
- GET /api/v1/weather/marine-grid GeoJSON output for wave data
- GET /api/v1/weather/point nearest neighbor lookup, distance_km, and hourly series
- Bounding box validation errors (422)
- Coordinate validation errors (422)
- 404 behavior when database is empty
- Response caching via get_or_compute
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from geoalchemy2.shape import from_shape
from httpx import ASGITransport, AsyncClient
from shapely.geometry import Point
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.grid_forecast import MarineGridForecast, WeatherGridForecast
from scripts.seed_india_area import seed_india_area


@pytest_asyncio.fixture
async def weather_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def seed_grid_data(db_session: AsyncSession):
    """Seed test grid points for Mumbai region and Arabian Sea."""
    await db_session.execute(text("DELETE FROM marine_grid_forecast"))
    await db_session.execute(text("DELETE FROM weather_grid_forecast"))
    await db_session.commit()

    now = datetime(2026, 10, 2, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 2, 1, 0, tzinfo=timezone.utc)

    # Weather points: (20.0, 72.5) and (22.5, 75.0)
    w_records = [
        WeatherGridForecast(
            id=uuid.uuid4(),
            latitude=20.0,
            longitude=72.5,
            valid_time=now,
            temperature_2m=28.5,
            precipitation=0.0,
            wind_speed_10m=12.4,
            wind_direction_10m=210,
            pressure_msl=1012.3,
            geom=from_shape(Point(72.5, 20.0), srid=4326),
            source_name="OPEN_METEO",
            fetched_at=now,
        ),
        WeatherGridForecast(
            id=uuid.uuid4(),
            latitude=20.0,
            longitude=72.5,
            valid_time=t1,
            temperature_2m=27.9,
            precipitation=0.5,
            wind_speed_10m=13.0,
            wind_direction_10m=215,
            pressure_msl=1012.8,
            geom=from_shape(Point(72.5, 20.0), srid=4326),
            source_name="OPEN_METEO",
            fetched_at=now,
        ),
        WeatherGridForecast(
            id=uuid.uuid4(),
            latitude=22.5,
            longitude=75.0,
            valid_time=now,
            temperature_2m=31.2,
            precipitation=0.0,
            wind_speed_10m=8.5,
            wind_direction_10m=180,
            pressure_msl=1010.5,
            geom=from_shape(Point(75.0, 22.5), srid=4326),
            source_name="OPEN_METEO",
            fetched_at=now,
        ),
    ]
    db_session.add_all(w_records)

    # Marine point: (20.0, 72.5)
    m_records = [
        MarineGridForecast(
            id=uuid.uuid4(),
            latitude=20.0,
            longitude=72.5,
            valid_time=now,
            wave_height=1.2,
            wave_direction=205.0,
            wave_period=7.8,
            geom=from_shape(Point(72.5, 20.0), srid=4326),
            source_name="OPEN_METEO_MARINE",
            fetched_at=now,
        ),
        MarineGridForecast(
            id=uuid.uuid4(),
            latitude=20.0,
            longitude=72.5,
            valid_time=t1,
            wave_height=1.3,
            wave_direction=210.0,
            wave_period=8.0,
            geom=from_shape(Point(72.5, 20.0), srid=4326),
            source_name="OPEN_METEO_MARINE",
            fetched_at=now,
        ),
    ]
    db_session.add_all(m_records)
    await db_session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Test Cases
# ─────────────────────────────────────────────────────────────────────────────


class TestWeatherGridEndpoints:
    """Test suite for /api/v1/weather/* routes."""

    @pytest.mark.asyncio
    async def test_get_weather_grid_geojson(self, weather_client: AsyncClient, seed_grid_data: None):
        """Should return GeoJSON FeatureCollection of weather forecast points."""
        resp = await weather_client.get("/api/v1/weather/grid?valid_time=2026-10-02T00:00:00Z")
        assert resp.status_code == 200
        data = resp.json()

        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 2  # Two distinct points at valid_time 00:00
        feat = data["features"][0]
        assert feat["type"] == "Feature"
        assert feat["geometry"]["type"] == "Point"
        assert len(feat["geometry"]["coordinates"]) == 2
        assert "temperature_2m" in feat["properties"]
        assert "pressure_msl" in feat["properties"]
        assert feat["properties"]["source_name"] == "OPEN_METEO"

    @pytest.mark.asyncio
    async def test_get_weather_grid_bbox_filter(self, weather_client: AsyncClient, seed_grid_data: None):
        """Bbox query parameter should filter features to within coordinates."""
        # Box covering only (20.0, 72.5) but excluding (22.5, 75.0)
        resp = await weather_client.get(
            "/api/v1/weather/grid?bbox=72.0,19.0,73.0,21.0&valid_time=2026-10-02T00:00:00Z"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["features"]) == 1
        coords = data["features"][0]["geometry"]["coordinates"]
        assert coords == [72.5, 20.0]

    @pytest.mark.asyncio
    async def test_get_weather_grid_invalid_bbox_422(self, weather_client: AsyncClient):
        """Malformed bbox format should return 422 Unprocessable Entity."""
        resp = await weather_client.get("/api/v1/weather/grid?bbox=invalid,bbox")
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_get_marine_grid_geojson(self, weather_client: AsyncClient, seed_grid_data: None):
        """Should return GeoJSON FeatureCollection of marine wave points."""
        resp = await weather_client.get("/api/v1/weather/marine-grid?valid_time=2026-10-02T00:00:00Z")
        assert resp.status_code == 200
        data = resp.json()

        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 1
        feat = data["features"][0]
        assert feat["geometry"]["coordinates"] == [72.5, 20.0]
        assert feat["properties"]["wave_height"] == 1.2
        assert feat["properties"]["wave_period"] == 7.8
        assert feat["properties"]["source_name"] == "OPEN_METEO_MARINE"

    @pytest.mark.asyncio
    async def test_get_weather_point_nearest_neighbor(
        self, weather_client: AsyncClient, seed_grid_data: None
    ):
        """Querying coordinates near Mumbai (19.076, 72.877) should snap to nearest grid point (20.0, 72.5)."""
        resp = await weather_client.get("/api/v1/weather/point?lat=19.076&lon=72.877")
        assert resp.status_code == 200
        data = resp.json()

        assert data["requested_latitude"] == 19.076
        assert data["requested_longitude"] == 72.877
        assert data["grid_latitude"] == 20.0
        assert data["grid_longitude"] == 72.5
        assert data["distance_km"] > 0
        assert data["distance_km"] < 150.0  # Approx 108km between Mumbai and (20.0, 72.5)
        assert len(data["hourly"]) == 2

        # Check hourly metrics
        h0 = data["hourly"][0]
        assert h0["temperature_2m"] == 28.5
        assert h0["wave_height"] == 1.2  # Sea point has marine data merged
        assert h0["wave_period"] == 7.8

    @pytest.mark.asyncio
    async def test_get_weather_point_validation_error_422(self, weather_client: AsyncClient):
        """Invalid lat/lon values out of bounds should return 422."""
        resp = await weather_client.get("/api/v1/weather/point?lat=120.0&lon=70.0")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_get_weather_grid_default_closest_valid_time(
        self, weather_client: AsyncClient, db_session: AsyncSession
    ):
        """When valid_time is omitted, default to the stored valid_time closest to current UTC hour (not the latest)."""
        await db_session.execute(text("DELETE FROM weather_grid_forecast"))
        await db_session.commit()

        now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        t_past = now_utc - timedelta(hours=6)
        t_closest = now_utc
        t_future = now_utc + timedelta(hours=72)

        records = [
            WeatherGridForecast(
                id=uuid.uuid4(),
                latitude=20.0,
                longitude=72.5,
                valid_time=t_past,
                temperature_2m=20.0,
                geom=from_shape(Point(72.5, 20.0), srid=4326),
                source_name="OPEN_METEO",
                fetched_at=now_utc,
            ),
            WeatherGridForecast(
                id=uuid.uuid4(),
                latitude=20.0,
                longitude=72.5,
                valid_time=t_closest,
                temperature_2m=25.0,
                geom=from_shape(Point(72.5, 20.0), srid=4326),
                source_name="OPEN_METEO",
                fetched_at=now_utc,
            ),
            WeatherGridForecast(
                id=uuid.uuid4(),
                latitude=20.0,
                longitude=72.5,
                valid_time=t_future,
                temperature_2m=30.0,
                geom=from_shape(Point(72.5, 20.0), srid=4326),
                source_name="OPEN_METEO",
                fetched_at=now_utc,
            ),
        ]
        db_session.add_all(records)
        await db_session.commit()

        resp = await weather_client.get("/api/v1/weather/grid")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["features"]) == 1
        feat = data["features"][0]
        assert feat["properties"]["temperature_2m"] == 25.0
        assert data["meta"]["valid_time"] == t_closest.isoformat()

    @pytest.mark.asyncio
    async def test_get_marine_grid_default_closest_valid_time(
        self, weather_client: AsyncClient, db_session: AsyncSession
    ):
        """When valid_time is omitted, default to the stored marine valid_time closest to current UTC hour."""
        await db_session.execute(text("DELETE FROM marine_grid_forecast"))
        await db_session.commit()

        now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        t_past = now_utc - timedelta(hours=6)
        t_closest = now_utc
        t_future = now_utc + timedelta(hours=72)

        records = [
            MarineGridForecast(
                id=uuid.uuid4(),
                latitude=20.0,
                longitude=72.5,
                valid_time=t_past,
                wave_height=0.5,
                geom=from_shape(Point(72.5, 20.0), srid=4326),
                source_name="OPEN_METEO_MARINE",
                fetched_at=now_utc,
            ),
            MarineGridForecast(
                id=uuid.uuid4(),
                latitude=20.0,
                longitude=72.5,
                valid_time=t_closest,
                wave_height=1.5,
                geom=from_shape(Point(72.5, 20.0), srid=4326),
                source_name="OPEN_METEO_MARINE",
                fetched_at=now_utc,
            ),
            MarineGridForecast(
                id=uuid.uuid4(),
                latitude=20.0,
                longitude=72.5,
                valid_time=t_future,
                wave_height=3.0,
                geom=from_shape(Point(72.5, 20.0), srid=4326),
                source_name="OPEN_METEO_MARINE",
                fetched_at=now_utc,
            ),
        ]
        db_session.add_all(records)
        await db_session.commit()

        resp = await weather_client.get("/api/v1/weather/marine-grid")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["features"]) == 1
        feat = data["features"][0]
        assert feat["properties"]["wave_height"] == 1.5
        assert data["meta"]["valid_time"] == t_closest.isoformat()

    @pytest.mark.asyncio
    async def test_get_weather_live_check_success(
        self, weather_client: AsyncClient, seed_grid_data: None
    ):
        """Live check should snap to nearest grid point and query mock Open-Meteo server-side."""
        mock_weather_payload = {
            "hourly": {
                "time": ["2026-10-02T00:00", "2026-10-02T01:00"],
                "temperature_2m": [28.5, 27.9],
                "precipitation": [0.0, 0.5],
                "wind_speed_10m": [12.4, 13.0],
                "wind_direction_10m": [210.0, 215.0],
                "pressure_msl": [1012.3, 1012.8],
            }
        }
        mock_marine_payload = {
            "hourly": {
                "time": ["2026-10-02T00:00", "2026-10-02T01:00"],
                "wave_height": [1.2, 1.3],
                "wave_direction": [205.0, 210.0],
                "wave_period": [7.8, 8.0],
            }
        }

        import httpx
        orig_get = httpx.AsyncClient.get

        async def mock_get(self_client, url, *args, **kwargs):
            url_str = str(url)
            if "open-meteo.com" in url_str:
                if "marine" in url_str:
                    return httpx.Response(200, json=mock_marine_payload)
                return httpx.Response(200, json=mock_weather_payload)
            return await orig_get(self_client, url, *args, **kwargs)

        with patch("httpx.AsyncClient.get", new=mock_get):
            resp = await weather_client.get("/api/v1/weather/live-check?lat=19.076&lon=72.877")
            assert resp.status_code == 200
            data = resp.json()
            assert data["requested_latitude"] == 19.076
            assert data["requested_longitude"] == 72.877
            assert data["grid_latitude"] == 20.0
            assert data["grid_longitude"] == 72.5
            assert data["distance_km"] > 0
            assert data["is_sea"] is True
            assert "live_fetched_at" in data
            assert len(data["hourly"]) == 2
            assert data["hourly"][0]["temperature_2m"] == 28.5
            assert data["hourly"][0]["wave_height"] == 1.2

    @pytest.mark.asyncio
    async def test_get_weather_live_check_out_of_bounds_422(
        self, weather_client: AsyncClient
    ):
        """Live check query outside platform bbox (Lat 0-40, Lon 60-100) returns 422."""
        resp = await weather_client.get("/api/v1/weather/live-check?lat=55.0&lon=70.0")
        assert resp.status_code == 422
        err = resp.json()
        assert err["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_get_weather_times(
        self, weather_client: AsyncClient, seed_grid_data
    ):
        """GET /api/v1/weather/times returns distinct sorted valid_times and latest_fetched_at."""
        resp = await weather_client.get("/api/v1/weather/times")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert len(data["valid_times"]) == 2
        assert data["valid_times"][0] < data["valid_times"][1]
        assert data["latest_fetched_at"] is not None
        assert "2026-10-02" in data["latest_fetched_at"]

    @pytest.mark.asyncio
    async def test_get_weather_grid_clip(
        self, weather_client: AsyncClient, db_session: AsyncSession, seed_grid_data
    ):
        """GET /api/v1/weather/grid?clip=true filters out points outside India land or EEZ."""
        await seed_india_area(db_session)

        # Use an isolated valid_time (05:00 UTC) to avoid cache collision with earlier tests
        vt_clip = datetime(2026, 10, 2, 5, 0, tzinfo=timezone.utc)
        pts = [
            # 1. Inside India land
            WeatherGridForecast(
                id=uuid.uuid4(),
                latitude=22.5,
                longitude=75.0,
                valid_time=vt_clip,
                temperature_2m=30.0,
                geom=from_shape(Point(75.0, 22.5), srid=4326),
                source_name="OPEN_METEO",
                fetched_at=vt_clip,
            ),
            # 2. Inside India EEZ
            WeatherGridForecast(
                id=uuid.uuid4(),
                latitude=20.0,
                longitude=72.5,
                valid_time=vt_clip,
                temperature_2m=28.0,
                geom=from_shape(Point(72.5, 20.0), srid=4326),
                source_name="OPEN_METEO",
                fetched_at=vt_clip,
            ),
            # 3. Far outside (equator / international waters)
            WeatherGridForecast(
                id=uuid.uuid4(),
                latitude=0.0,
                longitude=60.0,
                valid_time=vt_clip,
                temperature_2m=26.0,
                geom=from_shape(Point(60.0, 0.0), srid=4326),
                source_name="OPEN_METEO",
                fetched_at=vt_clip,
            ),
        ]
        db_session.add_all(pts)
        await db_session.commit()

        # Without clip (clip=false): should return all 3 points
        resp_unclipped = await weather_client.get("/api/v1/weather/grid?valid_time=2026-10-02T05:00:00Z&clip=false")
        assert resp_unclipped.status_code == 200
        unclipped_features = resp_unclipped.json()["features"]
        assert len(unclipped_features) == 3

        # With clip (clip=true): should filter out (0.0, 60.0) and return only 2 points inside India land/EEZ
        resp_clipped = await weather_client.get("/api/v1/weather/grid?valid_time=2026-10-02T05:00:00Z&clip=true")
        assert resp_clipped.status_code == 200
        clipped_features = resp_clipped.json()["features"]
        assert len(clipped_features) == 2
        coords = [f["geometry"]["coordinates"] for f in clipped_features]
        assert [60.0, 0.0] not in coords
        assert [75.0, 22.5] in coords
        assert [72.5, 20.0] in coords

    @pytest.mark.asyncio
    async def test_get_marine_grid_clip(
        self, weather_client: AsyncClient, db_session: AsyncSession, seed_grid_data
    ):
        """GET /api/v1/weather/marine-grid?clip=true filters out points outside India EEZ."""
        await seed_india_area(db_session)

        # Use an isolated valid_time (06:00 UTC) to avoid cache collision
        vt_clip = datetime(2026, 10, 2, 6, 0, tzinfo=timezone.utc)
        pts = [
            # 1. Inside India EEZ
            MarineGridForecast(
                id=uuid.uuid4(),
                latitude=20.0,
                longitude=72.5,
                valid_time=vt_clip,
                wave_height=1.5,
                wave_direction=200.0,
                wave_period=7.0,
                geom=from_shape(Point(72.5, 20.0), srid=4326),
                source_name="OPEN_METEO_MARINE",
                fetched_at=vt_clip,
            ),
            # 2. Outside India EEZ
            MarineGridForecast(
                id=uuid.uuid4(),
                latitude=0.0,
                longitude=60.0,
                valid_time=vt_clip,
                wave_height=2.0,
                wave_direction=180.0,
                wave_period=6.0,
                geom=from_shape(Point(60.0, 0.0), srid=4326),
                source_name="OPEN_METEO_MARINE",
                fetched_at=vt_clip,
            ),
        ]
        db_session.add_all(pts)
        await db_session.commit()

        # Without clip: 2 marine points at 06:00
        resp_unclipped = await weather_client.get("/api/v1/weather/marine-grid?valid_time=2026-10-02T06:00:00Z&clip=false")
        assert resp_unclipped.status_code == 200
        assert len(resp_unclipped.json()["features"]) == 2

        # With clip: only 1 point inside India EEZ (20.0, 72.5)
        resp_clipped = await weather_client.get("/api/v1/weather/marine-grid?valid_time=2026-10-02T06:00:00Z&clip=true")
        assert resp_clipped.status_code == 200
        clipped = resp_clipped.json()["features"]
        assert len(clipped) == 1
        assert clipped[0]["geometry"]["coordinates"] == [72.5, 20.0]
