"""Open-Meteo Gridded Weather & Marine Forecast Ingestion Adapter (India & EEZ Domain).

Polls the free Open-Meteo Forecast and Marine APIs for gridded forecasts
covering the territorial extent of India and its Exclusive Economic Zone (EEZ):
  - Latitude: 0°N to 40°N
  - Longitude: 60°E to 100°E
  - Default grid step: 2.5°
  - Batched coordinate requests respecting rate limits

Persists forecast data directly into:
  - `weather_grid_forecast`: temperature_2m, precipitation, wind_speed_10m,
                             wind_direction_10m, pressure_msl
  - `marine_grid_forecast`: wave_height, wave_direction, wave_period (for sea points)

Architectural Invariant:
  These rows represent continuous numerical weather model forecasts, NOT discrete
  hazard incidents or citizen observations. They are stored directly in dedicated
  PostGIS tables and are NOT routed through the incident pipeline or Redis streams.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.grid_forecast import MarineGridForecast, WeatherGridForecast

logger = logging.getLogger(__name__)


def is_sea_point(lat: float, lon: float) -> bool:
    """Classify whether a coordinate within the (lat 0-40, lon 60-100) EEZ grid lies in maritime water.

    Maritime domain logic:
    - Coordinates > 25.5°N are inland landmass (North India, Pakistan, Himalayas, Tibet, China).
    - Coordinates <= 8.0°N across 60°E-100°E are in the open Indian Ocean / equatorial waters.
    - Arabian Sea (west of Indian coastline):
        - lat <= 20.0°N and lon <= 72.5°E
        - 20.0°N < lat <= 25.0°N and lon <= 69.0°E (Arabian sea)
    - Bay of Bengal & Andaman Sea (east of Indian coastline):
        - 8.0°N < lat <= 16.0°N and lon >= 80.5°E
        - 16.0°N < lat <= 22.0°N and lon >= 85.0°E
        - lat <= 14.0°N and lon >= 91.0°E (Andaman and Nicobar waters)
    """
    if lat > 25.5:
        return False
    if lat <= 8.0:
        return True
    if lat <= 20.0 and lon <= 72.5:
        return True
    if 20.0 < lat <= 25.0 and lon <= 69.0:
        return True
    if 8.0 < lat <= 16.0 and lon >= 80.5:
        return True
    if 16.0 < lat <= 22.0 and lon >= 85.0:
        return True
    if lat <= 14.0 and lon >= 91.0:
        return True
    return False


def generate_grid_points(
    lat_min: float = 0.0,
    lat_max: float = 40.0,
    lon_min: float = 60.0,
    lon_max: float = 100.0,
    step: float = 2.5,
) -> List[Tuple[float, float]]:
    """Generate deterministic (lat, lon) coordinates covering the bounding domain."""
    num_lat = int(round((lat_max - lat_min) / step)) + 1
    num_lon = int(round((lon_max - lon_min) / step)) + 1
    points: List[Tuple[float, float]] = []
    for i in range(num_lat):
        lat = round(lat_min + i * step, 4)
        for j in range(num_lon):
            lon = round(lon_min + j * step, 4)
            points.append((lat, lon))
    return points


def chunk_points(
    points: Sequence[Tuple[float, float]],
    batch_size: int,
) -> List[List[Tuple[float, float]]]:
    """Slice coordinate tuples into batches."""
    if batch_size <= 0:
        batch_size = 25
    return [list(points[i : i + batch_size]) for i in range(0, len(points), batch_size)]


def _safe_float(lst: Optional[List[Any]], idx: int) -> Optional[float]:
    if not lst or idx >= len(lst):
        return None
    val = lst[idx]
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


class GriddedForecastAdapter:
    """Ingestion adapter for Open-Meteo multi-point gridded weather and marine forecasts."""

    USER_AGENT = "NationalWeatherPlatform-SIH26069/1.0 (sih26069@weather-platform.gov.in)"

    WEATHER_VARIABLES = [
        "temperature_2m",
        "precipitation",
        "wind_speed_10m",
        "wind_direction_10m",
        "pressure_msl",
    ]

    MARINE_VARIABLES = [
        "wave_height",
        "wave_direction",
        "wave_period",
    ]

    def __init__(
        self,
        weather_endpoint: Optional[str] = None,
        marine_endpoint: Optional[str] = None,
        lat_min: Optional[float] = None,
        lat_max: Optional[float] = None,
        lon_min: Optional[float] = None,
        lon_max: Optional[float] = None,
        step_degrees: Optional[float] = None,
        batch_size: Optional[int] = None,
        interval_seconds: Optional[float] = None,
        timeout_seconds: Optional[float] = None,
        min_interval_seconds: Optional[float] = None,
        forecast_days: Optional[int] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        session_factory: Optional[Callable[[], AsyncSession]] = None,
    ) -> None:
        self.source_code = "GRIDDED_FORECAST"
        self.source_name = "OPEN_METEO"
        self.marine_source_name = "OPEN_METEO_MARINE"
        self.source_type = "METEOROLOGICAL_SERVICE"
        self.base_trust_score = 0.85

        self.weather_endpoint = weather_endpoint or getattr(
            settings, "GRID_FORECAST_WEATHER_ENDPOINT", "https://api.open-meteo.com/v1/forecast"
        )
        self.marine_endpoint = marine_endpoint or getattr(
            settings, "GRID_FORECAST_MARINE_ENDPOINT", "https://marine-api.open-meteo.com/v1/marine"
        )
        self.lat_min = lat_min if lat_min is not None else getattr(settings, "GRID_FORECAST_LAT_MIN", 0.0)
        self.lat_max = lat_max if lat_max is not None else getattr(settings, "GRID_FORECAST_LAT_MAX", 40.0)
        self.lon_min = lon_min if lon_min is not None else getattr(settings, "GRID_FORECAST_LON_MIN", 60.0)
        self.lon_max = lon_max if lon_max is not None else getattr(settings, "GRID_FORECAST_LON_MAX", 100.0)
        self.step_degrees = (
            step_degrees if step_degrees is not None else getattr(settings, "GRID_FORECAST_STEP_DEGREES", 2.5)
        )
        self.batch_size = (
            batch_size if batch_size is not None else getattr(settings, "GRID_FORECAST_BATCH_SIZE", 25)
        )
        self.interval_seconds = (
            interval_seconds
            if interval_seconds is not None
            else getattr(settings, "GRID_FORECAST_INTERVAL_SECONDS", 21600.0)
        )
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else getattr(settings, "GRID_FORECAST_TIMEOUT_SECONDS", 20.0)
        )
        self.min_interval_seconds = (
            min_interval_seconds
            if min_interval_seconds is not None
            else getattr(settings, "GRID_FORECAST_MIN_REQUEST_INTERVAL_SECONDS", 1.0)
        )
        self.forecast_days = (
            forecast_days
            if forecast_days is not None
            else getattr(settings, "GRID_FORECAST_FORECAST_DAYS", 2)
        )

        self._http_client = http_client
        self._session_factory = session_factory or async_session_factory
        self._last_request_time: float = 0.0
        self._last_ingest_time: float = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client and not self._http_client.is_closed:
            return self._http_client
        return httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout_seconds),
            headers={"User-Agent": self.USER_AGENT},
            follow_redirects=True,
        )

    async def _apply_rate_limit(self) -> None:
        """Enforce rate limiting between batch requests."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.min_interval_seconds:
            await asyncio.sleep(self.min_interval_seconds - elapsed)
        self._last_request_time = time.monotonic()

    def _parse_weather_response(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        requested_batch: List[Tuple[float, float]],
        fetched_at: datetime,
    ) -> List[Dict[str, Any]]:
        """Parse batched Open-Meteo weather forecast JSON into flat table dictionaries."""
        data_list: List[Dict[str, Any]] = data if isinstance(data, list) else [data]
        records: List[Dict[str, Any]] = []

        for idx, item in enumerate(data_list):
            if not isinstance(item, dict):
                continue

            # Fall back to requested coordinates to preserve canonical grid step
            lat, lon = requested_batch[idx] if idx < len(requested_batch) else (
                item.get("latitude", 0.0), item.get("longitude", 0.0)
            )

            hourly = item.get("hourly")
            if not isinstance(hourly, dict):
                continue

            times: List[str] = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            precips = hourly.get("precipitation", [])
            wind_speeds = hourly.get("wind_speed_10m", [])
            wind_dirs = hourly.get("wind_direction_10m", [])
            pressures = hourly.get("pressure_msl", [])

            point_geom = from_shape(Point(lon, lat), srid=4326)

            for i, t_str in enumerate(times):
                try:
                    vt = datetime.fromisoformat(t_str)
                    if vt.tzinfo is None:
                        vt = vt.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    continue

                records.append({
                    "id": uuid.uuid4(),
                    "latitude": lat,
                    "longitude": lon,
                    "valid_time": vt,
                    "temperature_2m": _safe_float(temps, i),
                    "precipitation": _safe_float(precips, i),
                    "wind_speed_10m": _safe_float(wind_speeds, i),
                    "wind_direction_10m": _safe_float(wind_dirs, i),
                    "pressure_msl": _safe_float(pressures, i),
                    "geom": point_geom,
                    "source_name": self.source_name,
                    "fetched_at": fetched_at,
                })

        return records

    def _parse_marine_response(
        self,
        data: Union[Dict[str, Any], List[Dict[str, Any]]],
        requested_batch: List[Tuple[float, float]],
        fetched_at: datetime,
    ) -> List[Dict[str, Any]]:
        """Parse batched Open-Meteo marine forecast JSON into flat table dictionaries."""
        data_list: List[Dict[str, Any]] = data if isinstance(data, list) else [data]
        records: List[Dict[str, Any]] = []

        for idx, item in enumerate(data_list):
            if not isinstance(item, dict):
                continue

            lat, lon = requested_batch[idx] if idx < len(requested_batch) else (
                item.get("latitude", 0.0), item.get("longitude", 0.0)
            )

            hourly = item.get("hourly")
            if not isinstance(hourly, dict):
                continue

            times: List[str] = hourly.get("time", [])
            wave_heights = hourly.get("wave_height", [])
            wave_directions = hourly.get("wave_direction", [])
            wave_periods = hourly.get("wave_period", [])

            point_geom = from_shape(Point(lon, lat), srid=4326)

            for i, t_str in enumerate(times):
                try:
                    vt = datetime.fromisoformat(t_str)
                    if vt.tzinfo is None:
                        vt = vt.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    continue

                wh = _safe_float(wave_heights, i)
                wd = _safe_float(wave_directions, i)
                wp = _safe_float(wave_periods, i)

                # Only persist if at least one marine metric exists
                if wh is not None or wd is not None or wp is not None:
                    records.append({
                        "id": uuid.uuid4(),
                        "latitude": lat,
                        "longitude": lon,
                        "valid_time": vt,
                        "wave_height": wh,
                        "wave_direction": wd,
                        "wave_period": wp,
                        "geom": point_geom,
                        "source_name": self.marine_source_name,
                        "fetched_at": fetched_at,
                    })

        return records

    async def _upsert_weather_batch(
        self,
        session: AsyncSession,
        records: List[Dict[str, Any]],
    ) -> int:
        """Upsert weather grid records on conflict (latitude, longitude, valid_time)."""
        if not records:
            return 0

        stmt = insert(WeatherGridForecast).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_weather_grid_forecast_lat_lon_time",
            set_={
                "temperature_2m": stmt.excluded.temperature_2m,
                "precipitation": stmt.excluded.precipitation,
                "wind_speed_10m": stmt.excluded.wind_speed_10m,
                "wind_direction_10m": stmt.excluded.wind_direction_10m,
                "pressure_msl": stmt.excluded.pressure_msl,
                "geom": stmt.excluded.geom,
                "source_name": stmt.excluded.source_name,
                "fetched_at": stmt.excluded.fetched_at,
            },
        )
        await session.execute(stmt)
        await session.commit()
        return len(records)

    async def _upsert_marine_batch(
        self,
        session: AsyncSession,
        records: List[Dict[str, Any]],
    ) -> int:
        """Upsert marine grid records on conflict (latitude, longitude, valid_time)."""
        if not records:
            return 0

        stmt = insert(MarineGridForecast).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_marine_grid_forecast_lat_lon_time",
            set_={
                "wave_height": stmt.excluded.wave_height,
                "wave_direction": stmt.excluded.wave_direction,
                "wave_period": stmt.excluded.wave_period,
                "geom": stmt.excluded.geom,
                "source_name": stmt.excluded.source_name,
                "fetched_at": stmt.excluded.fetched_at,
            },
        )
        await session.execute(stmt)
        await session.commit()
        return len(records)

    async def _fetch_weather_batch(
        self,
        client: httpx.AsyncClient,
        batch: List[Tuple[float, float]],
    ) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Execute a batched GET request to Open-Meteo Weather Forecast API."""
        await self._apply_rate_limit()
        lats = ",".join(str(lat) for lat, _ in batch)
        lons = ",".join(str(lon) for _, lon in batch)
        params = {
            "latitude": lats,
            "longitude": lons,
            "hourly": ",".join(self.WEATHER_VARIABLES),
            "forecast_days": self.forecast_days,
            "timezone": "UTC",
        }

        try:
            resp = await client.get(str(self.weather_endpoint), params=params)
            if resp.status_code != 200:
                logger.warning(
                    "Open-Meteo weather forecast returned HTTP %d: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return None
            return resp.json()
        except httpx.TimeoutException:
            logger.warning("Open-Meteo weather forecast batch request timed out.")
            return None
        except Exception as e:
            logger.error("Error fetching weather forecast batch: %s", e, exc_info=True)
            return None

    async def _fetch_marine_batch(
        self,
        client: httpx.AsyncClient,
        batch: List[Tuple[float, float]],
    ) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Execute a batched GET request to Open-Meteo Marine API for sea points."""
        await self._apply_rate_limit()
        lats = ",".join(str(lat) for lat, _ in batch)
        lons = ",".join(str(lon) for _, lon in batch)
        params = {
            "latitude": lats,
            "longitude": lons,
            "hourly": ",".join(self.MARINE_VARIABLES),
            "forecast_days": self.forecast_days,
            "timezone": "UTC",
        }

        try:
            resp = await client.get(str(self.marine_endpoint), params=params)
            if resp.status_code != 200:
                logger.warning(
                    "Open-Meteo marine forecast returned HTTP %d: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return None
            return resp.json()
        except httpx.TimeoutException:
            logger.warning("Open-Meteo marine forecast batch request timed out.")
            return None
        except Exception as e:
            logger.error("Error fetching marine forecast batch: %s", e, exc_info=True)
            return None

    async def fetch_and_store_weather(
        self,
        session: AsyncSession,
        points: List[Tuple[float, float]],
        client: httpx.AsyncClient,
        fetched_at: datetime,
    ) -> int:
        """Fetch and persist weather grid forecasts across batches."""
        batches = chunk_points(points, self.batch_size)
        total_stored = 0

        for batch in batches:
            raw_data = await self._fetch_weather_batch(client, batch)
            if raw_data:
                records = self._parse_weather_response(raw_data, batch, fetched_at)
                count = await self._upsert_weather_batch(session, records)
                total_stored += count

        return total_stored

    async def fetch_and_store_marine(
        self,
        session: AsyncSession,
        points: List[Tuple[float, float]],
        client: httpx.AsyncClient,
        fetched_at: datetime,
    ) -> int:
        """Fetch and persist marine grid forecasts across sea point batches."""
        sea_points = [p for p in points if is_sea_point(p[0], p[1])]
        if not sea_points:
            return 0

        batches = chunk_points(sea_points, self.batch_size)
        total_stored = 0

        for batch in batches:
            raw_data = await self._fetch_marine_batch(client, batch)
            if raw_data:
                records = self._parse_marine_response(raw_data, batch, fetched_at)
                count = await self._upsert_marine_batch(session, records)
                total_stored += count

        return total_stored

    async def ingest(
        self,
        session: Optional[AsyncSession] = None,
        force: bool = False,
    ) -> List[Any]:
        """Execute complete gridded forecast ingestion cycle.

        Pulls Open-Meteo weather and marine forecast data for the India & EEZ grid domain,
        and stores them directly into weather_grid_forecast and marine_grid_forecast.

        Returns an empty list so NO events are routed through incident/observation streams.
        """
        now = time.monotonic()
        if (
            not force
            and self._last_ingest_time > 0
            and self.interval_seconds > 0
            and (now - self._last_ingest_time) < self.interval_seconds
        ):
            logger.info(
                "GriddedForecastAdapter: interval %.1fs not reached yet. Skipping.",
                self.interval_seconds,
            )
            return []

        grid_points = generate_grid_points(
            lat_min=self.lat_min,
            lat_max=self.lat_max,
            lon_min=self.lon_min,
            lon_max=self.lon_max,
            step=self.step_degrees,
        )

        logger.info(
            "GriddedForecastAdapter: Starting grid ingestion covering %d coordinates (step=%.1f°)...",
            len(grid_points),
            self.step_degrees,
        )

        client = await self._get_client()
        should_close = client != self._http_client
        fetched_at = datetime.now(timezone.utc)

        try:
            if session is not None:
                weather_count = await self.fetch_and_store_weather(session, grid_points, client, fetched_at)
                marine_count = await self.fetch_and_store_marine(session, grid_points, client, fetched_at)
            else:
                async with self._session_factory() as s:
                    weather_count = await self.fetch_and_store_weather(s, grid_points, client, fetched_at)
                    marine_count = await self.fetch_and_store_marine(s, grid_points, client, fetched_at)

            self._last_ingest_time = time.monotonic()
            logger.info(
                "GriddedForecastAdapter complete: persisted %d weather forecasts, %d marine forecasts.",
                weather_count,
                marine_count,
            )
        finally:
            if should_close:
                await client.aclose()

        # Invariant: return empty list to prevent streaming into incident / observation pipeline
        return []
