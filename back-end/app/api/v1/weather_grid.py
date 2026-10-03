"""Gridded Weather & Marine Forecast API Router.

Provides read-only access to ingested Open-Meteo numerical weather and marine
grid forecasts covering India and its Exclusive Economic Zone (EEZ):
  - GET /api/v1/weather/grid: GeoJSON FeatureCollection of weather grid points
  - GET /api/v1/weather/marine-grid: GeoJSON FeatureCollection of sea wave data
  - GET /api/v1/weather/point: Nearest grid point lookup with full hourly time-series
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_or_compute
from app.core.config import settings
from app.core.rate_limiter import get_client_ip, report_rate_limiter
from app.db.session import get_db
from app.ingestion.gridded_forecast_adapter import is_sea_point
from app.models.grid_forecast import MarineGridForecast, WeatherGridForecast
from app.models.india_area import IndiaArea

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Pydantic Response Schemas ────────────────────────────────────────────────


class GeoJSONGeometry(BaseModel):
    type: str = "Point"
    coordinates: List[float] = Field(..., description="[longitude, latitude]")


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: Dict[str, Any]


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]
    meta: Dict[str, Any] = Field(default_factory=dict)


class HourlyForecastItem(BaseModel):
    valid_time: str
    temperature_2m: Optional[float] = None
    precipitation: Optional[float] = None
    wind_speed_10m: Optional[float] = None
    wind_direction_10m: Optional[float] = None
    pressure_msl: Optional[float] = None
    wave_height: Optional[float] = None
    wave_direction: Optional[float] = None
    wave_period: Optional[float] = None


class NearestPointForecastResponse(BaseModel):
    grid_latitude: float
    grid_longitude: float
    requested_latitude: float
    requested_longitude: float
    distance_km: float
    fetched_at: str
    source_name: str
    hourly: List[HourlyForecastItem]


class LiveCheckResponse(BaseModel):
    requested_latitude: float
    requested_longitude: float
    grid_latitude: float
    grid_longitude: float
    distance_km: float
    is_sea: bool
    live_fetched_at: str
    hourly: List[HourlyForecastItem]


class WeatherTimesResponse(BaseModel):
    valid_times: List[str] = Field(..., description="Distinct available forecast valid times in ISO format")
    latest_fetched_at: Optional[str] = Field(None, description="Latest database ingestion timestamp")
    count: int = Field(..., description="Total count of available time steps")


# ─── Bounding Box Validation Helper ──────────────────────────────────────────


def _parse_bbox(bbox_str: Optional[str]) -> Optional[Tuple[float, float, float, float]]:
    """Parse and validate bounding box string: 'min_lon,min_lat,max_lon,max_lat'."""
    if not bbox_str:
        return None

    parts = bbox_str.split(",")
    if len(parts) != 4:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Invalid bbox format. Expected 'min_lon,min_lat,max_lon,max_lat'.",
            },
        )

    try:
        min_lon, min_lat, max_lon, max_lat = (float(p.strip()) for p in parts)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Invalid bbox coordinates. Values must be numeric floats.",
            },
        )

    if not (-180.0 <= min_lon <= 180.0 and -180.0 <= max_lon <= 180.0 and -90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Bounding box coordinates out of valid geographic ranges.",
            },
        )

    if min_lon > max_lon or min_lat > max_lat:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Invalid bbox range: min values must be <= max values.",
            },
        )

    return (min_lon, min_lat, max_lon, max_lat)


def _parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetime string into UTC-aware datetime."""
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_ERROR",
                "message": f"Invalid ISO datetime string: '{dt_str}'. Expected ISO 8601 format.",
            },
        )


# ─── Endpoints ────────────────────────────────────────────────────────────────
@router.get(
    "/times",
    response_model=WeatherTimesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Available Forecast Timestamps",
    description="Return distinct valid_times sorted chronologically, plus the latest database ingestion fetched_at timestamp.",
)
async def get_weather_times(
    db: AsyncSession = Depends(get_db),
):
    async def _compute():
        # Distinct valid_times ordered chronologically
        stmt_times = (
            select(WeatherGridForecast.valid_time)
            .distinct()
            .order_by(WeatherGridForecast.valid_time.asc())
        )
        times_result = (await db.execute(stmt_times)).scalars().all()

        # Latest fetched_at
        stmt_fetched = select(func.max(WeatherGridForecast.fetched_at))
        latest_fetched = await db.scalar(stmt_fetched)

        valid_times_iso = [vt.isoformat() for vt in times_result if vt]
        fetched_at_iso = latest_fetched.isoformat() if latest_fetched else None

        return {
            "valid_times": valid_times_iso,
            "latest_fetched_at": fetched_at_iso,
            "count": len(valid_times_iso),
        }

    return await get_or_compute(
        endpoint="weather:times",
        query_params={},
        compute_fn=_compute,
        ttl=60,
    )


@router.get(
    "/grid",
    response_model=GeoJSONFeatureCollection,
    status_code=status.HTTP_200_OK,
    summary="Get Weather Grid Forecast GeoJSON",
    description="Query gridded weather model forecast points within a bounding box at a given valid_time.",
)
async def get_weather_grid(
    bbox: Optional[str] = Query(None, description="Bounding box 'min_lon,min_lat,max_lon,max_lat'"),
    valid_time: Optional[str] = Query(None, description="ISO valid_time (e.g. 2026-10-02T00:00:00Z)"),
    clip: bool = Query(False, description="Clip points to India land or EEZ maritime boundaries"),
    db: AsyncSession = Depends(get_db),
):
    parsed_bbox = _parse_bbox(bbox)
    parsed_vt = _parse_iso_datetime(valid_time)

    params = {
        "bbox": bbox,
        "valid_time": valid_time,
        "clip": clip,
    }

    async def _compute():
        nonlocal parsed_vt
        # Resolve target valid_time if not provided (closest to current UTC hour)
        if parsed_vt is None:
            now_utc = datetime.now(timezone.utc)
            stmt_vt = (
                select(WeatherGridForecast.valid_time)
                .order_by(func.abs(func.extract("epoch", WeatherGridForecast.valid_time - now_utc)).asc())
                .limit(1)
            )
            parsed_vt = await db.scalar(stmt_vt)

        if parsed_vt is None:
            return {
                "type": "FeatureCollection",
                "features": [],
                "meta": {"count": 0, "message": "No gridded weather forecasts available in database."},
            }

        stmt = select(WeatherGridForecast).where(WeatherGridForecast.valid_time == parsed_vt)

        if parsed_bbox:
            min_lon, min_lat, max_lon, max_lat = parsed_bbox
            envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
            stmt = stmt.where(func.ST_Intersects(WeatherGridForecast.geom, envelope))

        if clip:
            stmt = stmt.where(
                select(IndiaArea.id)
                .where(func.ST_Intersects(IndiaArea.geom, WeatherGridForecast.geom))
                .exists()
            )

        stmt = stmt.order_by(WeatherGridForecast.latitude.asc(), WeatherGridForecast.longitude.asc()).limit(1000)
        rows = (await db.execute(stmt)).scalars().all()

        features = [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [row.longitude, row.latitude],
                },
                "properties": {
                    "id": str(row.id),
                    "latitude": row.latitude,
                    "longitude": row.longitude,
                    "valid_time": row.valid_time.isoformat(),
                    "temperature_2m": row.temperature_2m,
                    "precipitation": row.precipitation,
                    "wind_speed_10m": row.wind_speed_10m,
                    "wind_direction_10m": row.wind_direction_10m,
                    "pressure_msl": row.pressure_msl,
                    "source_name": row.source_name,
                    "fetched_at": row.fetched_at.isoformat(),
                },
            }
            for row in rows
        ]

        return {
            "type": "FeatureCollection",
            "features": features,
            "meta": {
                "count": len(features),
                "valid_time": parsed_vt.isoformat(),
            },
        }

    return await get_or_compute(
        endpoint="weather:grid",
        query_params=params,
        compute_fn=_compute,
        ttl=60,
    )


@router.get(
    "/marine-grid",
    response_model=GeoJSONFeatureCollection,
    status_code=status.HTTP_200_OK,
    summary="Get Marine Grid Forecast GeoJSON",
    description="Query gridded marine wave model forecast points within a bounding box at a given valid_time.",
)
async def get_marine_grid(
    bbox: Optional[str] = Query(None, description="Bounding box 'min_lon,min_lat,max_lon,max_lat'"),
    valid_time: Optional[str] = Query(None, description="ISO valid_time (e.g. 2026-10-02T00:00:00Z)"),
    clip: bool = Query(False, description="Clip points to India land or EEZ maritime boundaries"),
    db: AsyncSession = Depends(get_db),
):
    parsed_bbox = _parse_bbox(bbox)
    parsed_vt = _parse_iso_datetime(valid_time)

    params = {
        "bbox": bbox,
        "valid_time": valid_time,
        "clip": clip,
    }

    async def _compute():
        nonlocal parsed_vt
        # Resolve target valid_time if not provided (closest to current UTC hour)
        if parsed_vt is None:
            now_utc = datetime.now(timezone.utc)
            stmt_vt = (
                select(MarineGridForecast.valid_time)
                .order_by(func.abs(func.extract("epoch", MarineGridForecast.valid_time - now_utc)).asc())
                .limit(1)
            )
            parsed_vt = await db.scalar(stmt_vt)

        if parsed_vt is None:
            return {
                "type": "FeatureCollection",
                "features": [],
                "meta": {"count": 0, "message": "No marine grid forecasts available in database."},
            }

        stmt = select(MarineGridForecast).where(MarineGridForecast.valid_time == parsed_vt)

        if parsed_bbox:
            min_lon, min_lat, max_lon, max_lat = parsed_bbox
            envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
            stmt = stmt.where(func.ST_Intersects(MarineGridForecast.geom, envelope))

        if clip:
            stmt = stmt.where(
                select(IndiaArea.id)
                .where(func.ST_Intersects(IndiaArea.geom, MarineGridForecast.geom))
                .exists()
            )

        stmt = stmt.order_by(MarineGridForecast.latitude.asc(), MarineGridForecast.longitude.asc()).limit(1000)
        rows = (await db.execute(stmt)).scalars().all()

        features = [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [row.longitude, row.latitude],
                },
                "properties": {
                    "id": str(row.id),
                    "latitude": row.latitude,
                    "longitude": row.longitude,
                    "valid_time": row.valid_time.isoformat(),
                    "wave_height": row.wave_height,
                    "wave_direction": row.wave_direction,
                    "wave_period": row.wave_period,
                    "source_name": row.source_name,
                    "fetched_at": row.fetched_at.isoformat(),
                },
            }
            for row in rows
        ]

        return {
            "type": "FeatureCollection",
            "features": features,
            "meta": {
                "count": len(features),
                "valid_time": parsed_vt.isoformat(),
            },
        }

    return await get_or_compute(
        endpoint="weather:marine-grid",
        query_params=params,
        compute_fn=_compute,
        ttl=60,
    )


@router.get(
    "/point",
    response_model=NearestPointForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Nearest Grid Point Forecast Series",
    description="Locate the nearest stored forecast grid point and return its full hourly time-series.",
)
async def get_weather_point(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Target query latitude (-90 to 90)"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Target query longitude (-180 to 180)"),
    db: AsyncSession = Depends(get_db),
):
    params = {
        "lat": f"{round(lat, 4):.4f}",
        "lon": f"{round(lon, 4):.4f}",
    }

    async def _compute():
        # PostGIS great-circle distance in kilometers via ST_DistanceSphere
        user_point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
        dist_expr = func.ST_DistanceSphere(WeatherGridForecast.geom, user_point) / 1000.0

        nearest_stmt = (
            select(
                WeatherGridForecast.latitude,
                WeatherGridForecast.longitude,
                WeatherGridForecast.source_name,
                WeatherGridForecast.fetched_at,
                dist_expr.label("distance_km"),
            )
            .order_by(dist_expr.asc())
            .limit(1)
        )

        nearest_res = (await db.execute(nearest_stmt)).first()
        if not nearest_res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "NOT_FOUND",
                    "message": "No forecast grid points currently populated in the database.",
                },
            )

        grid_lat = float(nearest_res.latitude)
        grid_lon = float(nearest_res.longitude)
        source_name = str(nearest_res.source_name)
        fetched_at = nearest_res.fetched_at
        distance_km = round(float(nearest_res.distance_km), 2)

        # 2. Retrieve hourly weather forecast series
        w_stmt = (
            select(WeatherGridForecast)
            .where(
                WeatherGridForecast.latitude == grid_lat,
                WeatherGridForecast.longitude == grid_lon,
            )
            .order_by(WeatherGridForecast.valid_time.asc())
        )
        weather_rows = (await db.execute(w_stmt)).scalars().all()

        # 3. Retrieve hourly marine forecast series if available
        m_stmt = (
            select(MarineGridForecast)
            .where(
                MarineGridForecast.latitude == grid_lat,
                MarineGridForecast.longitude == grid_lon,
            )
            .order_by(MarineGridForecast.valid_time.asc())
        )
        marine_rows = (await db.execute(m_stmt)).scalars().all()
        marine_by_time: Dict[datetime, MarineGridForecast] = {m.valid_time: m for m in marine_rows}

        hourly: List[Dict[str, Any]] = []
        for w in weather_rows:
            m_item = marine_by_time.get(w.valid_time)
            hourly.append({
                "valid_time": w.valid_time.isoformat(),
                "temperature_2m": w.temperature_2m,
                "precipitation": w.precipitation,
                "wind_speed_10m": w.wind_speed_10m,
                "wind_direction_10m": w.wind_direction_10m,
                "pressure_msl": w.pressure_msl,
                "wave_height": m_item.wave_height if m_item else None,
                "wave_direction": m_item.wave_direction if m_item else None,
                "wave_period": m_item.wave_period if m_item else None,
            })

        return {
            "grid_latitude": grid_lat,
            "grid_longitude": grid_lon,
            "requested_latitude": lat,
            "requested_longitude": lon,
            "distance_km": distance_km,
            "fetched_at": fetched_at.isoformat(),
            "source_name": source_name,
            "hourly": hourly,
        }

    return await get_or_compute(
        endpoint="weather:point",
        query_params=params,
        compute_fn=_compute,
        ttl=60,
    )


@router.get(
    "/live-check",
    response_model=LiveCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Live Source Parity Check against Open-Meteo",
    description=(
        "Snaps input coordinates to the nearest stored numerical forecast grid point, "
        "then makes a server-side request directly to Open-Meteo for real-time model comparison."
    ),
)
async def get_weather_live_check(
    request: Request,
    lat: float = Query(..., ge=-90.0, le=90.0, description="Target query latitude (-90 to 90)"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Target query longitude (-180 to 180)"),
    db: AsyncSession = Depends(get_db),
):
    # 1. Bounding box domain validation
    lat_min = getattr(settings, "GRID_FORECAST_LAT_MIN", 0.0)
    lat_max = getattr(settings, "GRID_FORECAST_LAT_MAX", 40.0)
    lon_min = getattr(settings, "GRID_FORECAST_LON_MIN", 60.0)
    lon_max = getattr(settings, "GRID_FORECAST_LON_MAX", 100.0)

    if not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "VALIDATION_ERROR",
                "message": (
                    f"Coordinates ({lat}, {lon}) fall outside the platform forecast grid domain "
                    f"[Lat {lat_min} to {lat_max}, Lon {lon_min} to {lon_max}]."
                ),
            },
        )

    # 2. Rate limiting check per client IP
    client_ip = get_client_ip(request)
    rate_key = f"live_check:{client_ip}"
    limit = getattr(settings, "REPORT_RATE_LIMIT_PER_MINUTE", 10) * 2
    if not await report_rate_limiter.is_allowed_async(rate_key, max_requests=limit):
        retry_after = await report_rate_limiter.get_retry_after_async(rate_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMIT_EXCEEDED",
                "message": f"Too many live check requests. Please wait {retry_after} seconds before trying again.",
            },
            headers={"Retry-After": str(retry_after)},
        )

    params = {
        "lat": f"{round(lat, 4):.4f}",
        "lon": f"{round(lon, 4):.4f}",
    }

    async def _compute():
        # 3. Locate nearest stored grid point using PostGIS 2D ST_MakePoint + ST_SetSRID
        user_point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
        dist_expr = func.ST_DistanceSphere(WeatherGridForecast.geom, user_point) / 1000.0

        nearest_stmt = (
            select(
                WeatherGridForecast.latitude,
                WeatherGridForecast.longitude,
                dist_expr.label("distance_km"),
            )
            .order_by(dist_expr.asc())
            .limit(1)
        )
        nearest_res = (await db.execute(nearest_stmt)).first()
        if not nearest_res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "NOT_FOUND",
                    "message": "No forecast grid points currently populated in the database.",
                },
            )

        grid_lat = float(nearest_res.latitude)
        grid_lon = float(nearest_res.longitude)
        distance_km = round(float(nearest_res.distance_km), 2)
        is_sea = is_sea_point(grid_lat, grid_lon)
        live_fetched_at = datetime.now(timezone.utc).isoformat()

        # 4. Server-side fetch from Open-Meteo with short timeout
        weather_url = (
            f"{settings.GRID_FORECAST_WEATHER_ENDPOINT}"
            f"?latitude={grid_lat}&longitude={grid_lon}"
            f"&hourly=temperature_2m,precipitation,wind_speed_10m,wind_direction_10m,pressure_msl"
            f"&forecast_days={settings.GRID_FORECAST_FORECAST_DAYS}&timezone=UTC"
        )

        async with httpx.AsyncClient(timeout=8.0) as client:
            try:
                w_resp = await client.get(weather_url)
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail={
                        "code": "UPSTREAM_TIMEOUT",
                        "message": f"Timed out connecting to Open-Meteo weather API: {exc}",
                    },
                )

            if w_resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={
                        "code": "UPSTREAM_API_ERROR",
                        "message": f"Open-Meteo weather API returned HTTP {w_resp.status_code}",
                    },
                )
            w_data = w_resp.json().get("hourly", {})

            m_data: Dict[str, Any] = {}
            if is_sea:
                marine_url = (
                    f"{settings.GRID_FORECAST_MARINE_ENDPOINT}"
                    f"?latitude={grid_lat}&longitude={grid_lon}"
                    f"&hourly=wave_height,wave_direction,wave_period"
                    f"&forecast_days={settings.GRID_FORECAST_FORECAST_DAYS}&timezone=UTC"
                )
                try:
                    m_resp = await client.get(marine_url)
                    if m_resp.status_code == 200:
                        m_data = m_resp.json().get("hourly", {})
                except Exception as m_exc:
                    logger.warning("Live check marine fetch failed: %s", m_exc)

        times = w_data.get("time", [])
        temps = w_data.get("temperature_2m", [])
        precips = w_data.get("precipitation", [])
        winds = w_data.get("wind_speed_10m", [])
        wind_dirs = w_data.get("wind_direction_10m", [])
        pressures = w_data.get("pressure_msl", [])

        wave_hs = m_data.get("wave_height", [])
        wave_dirs = m_data.get("wave_direction", [])
        wave_pers = m_data.get("wave_period", [])

        hourly: List[Dict[str, Any]] = []
        for idx, t_raw in enumerate(times):
            vt_iso = t_raw + ":00+00:00" if len(t_raw) == 16 else t_raw
            hourly.append({
                "valid_time": vt_iso,
                "temperature_2m": temps[idx] if idx < len(temps) else None,
                "precipitation": precips[idx] if idx < len(precips) else None,
                "wind_speed_10m": winds[idx] if idx < len(winds) else None,
                "wind_direction_10m": wind_dirs[idx] if idx < len(wind_dirs) else None,
                "pressure_msl": pressures[idx] if idx < len(pressures) else None,
                "wave_height": wave_hs[idx] if idx < len(wave_hs) else None,
                "wave_direction": wave_dirs[idx] if idx < len(wave_dirs) else None,
                "wave_period": wave_pers[idx] if idx < len(wave_pers) else None,
            })

        return {
            "requested_latitude": lat,
            "requested_longitude": lon,
            "grid_latitude": grid_lat,
            "grid_longitude": grid_lon,
            "distance_km": distance_km,
            "is_sea": is_sea,
            "live_fetched_at": live_fetched_at,
            "hourly": hourly,
        }

    return await get_or_compute(
        endpoint="weather:live-check",
        query_params=params,
        compute_fn=_compute,
        ttl=60,
    )
