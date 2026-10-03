"""Live verification of GriddedForecastAdapter against Open-Meteo API.

Executes a live ingestion with force=True, inspects database row counts,
timestamps, and distinct sea points, and validates 3 points against
direct Open-Meteo API queries.
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import httpx
from sqlalchemy import func, select

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import async_session_factory  # noqa: E402
from app.ingestion.gridded_forecast_adapter import GriddedForecastAdapter  # noqa: E402
from app.models.grid_forecast import MarineGridForecast, WeatherGridForecast  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_live")


async def run_live_verification():
    print("=" * 80)
    print("STEP A: Running GriddedForecastAdapter with force=True against live Open-Meteo API")
    print("=" * 80)

    adapter = GriddedForecastAdapter(
        lat_min=0.0,
        lat_max=40.0,
        lon_min=60.0,
        lon_max=100.0,
        step_degrees=2.5,
        batch_size=25,
        min_interval_seconds=0.6,
        forecast_days=4,
    )

    failed_batches: List[str] = []
    original_fetch_weather = adapter._fetch_weather_batch
    original_fetch_marine = adapter._fetch_marine_batch

    async def tracking_fetch_weather(client, batch):
        res = await original_fetch_weather(client, batch)
        if res is None:
            failed_batches.append(f"Weather batch: {batch[:2]}... (size {len(batch)})")
        return res

    async def tracking_fetch_marine(client, batch):
        res = await original_fetch_marine(client, batch)
        if res is None:
            failed_batches.append(f"Marine batch: {batch[:2]}... (size {len(batch)})")
        return res

    adapter._fetch_weather_batch = tracking_fetch_weather  # type: ignore
    adapter._fetch_marine_batch = tracking_fetch_marine  # type: ignore

    start_time = datetime.now(timezone.utc)
    print(f"Starting live ingestion at {start_time.isoformat()}...")

    async with async_session_factory() as session:
        events = await adapter.ingest(session=session, force=True)

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()
    print(f"Live ingestion completed in {duration:.2f}s. Returned events count: {len(events)} (expected: 0)")

    # 1. Query table statistics
    async with async_session_factory() as session:
        # Weather table stats
        w_count = await session.scalar(select(func.count(WeatherGridForecast.id)))
        w_min_valid = await session.scalar(select(func.min(WeatherGridForecast.valid_time)))
        w_max_valid = await session.scalar(select(func.max(WeatherGridForecast.valid_time)))
        w_min_fetch = await session.scalar(select(func.min(WeatherGridForecast.fetched_at)))
        w_max_fetch = await session.scalar(select(func.max(WeatherGridForecast.fetched_at)))
        w_points = await session.scalar(
            select(func.count(func.distinct(func.concat(WeatherGridForecast.latitude, '_', WeatherGridForecast.longitude))))
        )

        # Marine table stats
        m_count = await session.scalar(select(func.count(MarineGridForecast.id)))
        m_min_valid = await session.scalar(select(func.min(MarineGridForecast.valid_time)))
        m_max_valid = await session.scalar(select(func.max(MarineGridForecast.valid_time)))
        m_min_fetch = await session.scalar(select(func.min(MarineGridForecast.fetched_at)))
        m_max_fetch = await session.scalar(select(func.max(MarineGridForecast.fetched_at)))
        m_points = await session.scalar(
            select(func.count(func.distinct(func.concat(MarineGridForecast.latitude, '_', MarineGridForecast.longitude))))
        )

    print("\n" + "-" * 80)
    print("DATABASE INGESTION STATISTICS REPORT:")
    print("-" * 80)
    print("Weather Grid Forecast (weather_grid_forecast):")
    print(f"  - Total Row Count:       {w_count}")
    print(f"  - Distinct Grid Points:   {w_points} (expected 289)")
    print(f"  - Min Valid Time (UTC):   {w_min_valid}")
    print(f"  - Max Valid Time (UTC):   {w_max_valid}")
    print(f"  - Min Fetched At (UTC):   {w_min_fetch}")
    print(f"  - Max Fetched At (UTC):   {w_max_fetch}")

    print("\nMarine Grid Forecast (marine_grid_forecast):")
    print(f"  - Total Row Count:       {m_count}")
    print(f"  - Distinct Sea Points:    {m_points}")
    print(f"  - Min Valid Time (UTC):   {m_min_valid}")
    print(f"  - Max Valid Time (UTC):   {m_max_valid}")
    print(f"  - Min Fetched At (UTC):   {m_min_fetch}")
    print(f"  - Max Fetched At (UTC):   {m_max_fetch}")

    print(f"\nFailed Batches: {len(failed_batches)}")
    if failed_batches:
        for fb in failed_batches:
            print(f"  - {fb}")
    else:
        print("  - None! All coordinate batches succeeded with HTTP 200.")

    # 2. Compare 3 grid points against direct Open-Meteo API curls
    test_points = [
        {"name": "Point 1: Inland Central India", "lat": 20.0, "lon": 80.0, "is_sea": False},
        {"name": "Point 2: Arabian Sea (EEZ)", "lat": 15.0, "lon": 65.0, "is_sea": True},
        {"name": "Point 3: Bay of Bengal (EEZ)", "lat": 12.5, "lon": 85.0, "is_sea": True},
    ]

    print("\n" + "=" * 80)
    print("COMPARING 3 POINTS AGAINST DIRECT OPEN-METEO API CALLS")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=15.0) as client:
        async with async_session_factory() as session:
            for pt in test_points:
                lat, lon = pt["lat"], pt["lon"]
                print(f"\n>>> Checking {pt['name']} at Lat={lat}, Lon={lon} (is_sea={pt['is_sea']}):")

                # Stored weather records from DB
                w_stmt = (
                    select(WeatherGridForecast)
                    .where(WeatherGridForecast.latitude == lat, WeatherGridForecast.longitude == lon)
                    .order_by(WeatherGridForecast.valid_time.asc())
                    .limit(5)
                )
                db_weather = (await session.execute(w_stmt)).scalars().all()

                # Direct API fetch for weather
                direct_w_url = (
                    f"https://api.open-meteo.com/v1/forecast"
                    f"?latitude={lat}&longitude={lon}"
                    f"&hourly=temperature_2m,precipitation,wind_speed_10m,wind_direction_10m,pressure_msl"
                    f"&forecast_days=4&timezone=UTC"
                )
                print(f"  Direct Weather API URL: {direct_w_url}")
                w_resp = await client.get(direct_w_url)
                direct_w = w_resp.json().get("hourly", {})

                # Compare first 3 timestamps
                diff_count = 0
                for idx in range(min(len(db_weather), 3)):
                    db_row = db_weather[idx]
                    api_temp = direct_w["temperature_2m"][idx]
                    api_precip = direct_w["precipitation"][idx]
                    api_ws = direct_w["wind_speed_10m"][idx]
                    api_wd = direct_w["wind_direction_10m"][idx]
                    api_p = direct_w["pressure_msl"][idx]

                    db_time_str = db_row.valid_time.strftime("%Y-%m-%dT%H:%M")
                    # Check equality
                    temp_match = abs((db_row.temperature_2m or 0) - (api_temp or 0)) < 0.01
                    precip_match = abs((db_row.precipitation or 0) - (api_precip or 0)) < 0.01
                    ws_match = abs((db_row.wind_speed_10m or 0) - (api_ws or 0)) < 0.01
                    wd_match = abs((db_row.wind_direction_10m or 0) - (api_wd or 0)) < 0.01
                    p_match = abs((db_row.pressure_msl or 0) - (api_p or 0)) < 0.01

                    matches = all([temp_match, precip_match, ws_match, wd_match, p_match])
                    if not matches:
                        diff_count += 1

                    status = "MATCH" if matches else "DIFF"
                    print(
                        f"    Hour {idx} [{db_time_str}]: {status} | "
                        f"DB temp={db_row.temperature_2m}°C, API temp={api_temp}°C | "
                        f"DB rain={db_row.precipitation}mm, API rain={api_precip}mm | "
                        f"DB wind={db_row.wind_speed_10m}km/h, API wind={api_ws}km/h | "
                        f"DB press={db_row.pressure_msl}hPa, API press={api_p}hPa"
                    )

                if pt["is_sea"]:
                    m_stmt = (
                        select(MarineGridForecast)
                        .where(MarineGridForecast.latitude == lat, MarineGridForecast.longitude == lon)
                        .order_by(MarineGridForecast.valid_time.asc())
                        .limit(5)
                    )
                    db_marine = (await session.execute(m_stmt)).scalars().all()

                    direct_m_url = (
                        f"https://marine-api.open-meteo.com/v1/marine"
                        f"?latitude={lat}&longitude={lon}"
                        f"&hourly=wave_height,wave_direction,wave_period"
                        f"&forecast_days=4&timezone=UTC"
                    )
                    print(f"  Direct Marine API URL: {direct_m_url}")
                    m_resp = await client.get(direct_m_url)
                    direct_m = m_resp.json().get("hourly", {})

                    for idx in range(min(len(db_marine), 3)):
                        db_row = db_marine[idx]
                        api_wh = direct_m["wave_height"][idx]
                        api_wd = direct_m["wave_direction"][idx]
                        api_wp = direct_m["wave_period"][idx]

                        db_time_str = db_row.valid_time.strftime("%Y-%m-%dT%H:%M")
                        wh_match = (
                            True
                            if (db_row.wave_height is None and api_wh is None)
                            else abs((db_row.wave_height or 0) - (api_wh or 0)) < 0.01
                        )
                        wd_match = (
                            True
                            if (db_row.wave_direction is None and api_wd is None)
                            else abs((db_row.wave_direction or 0) - (api_wd or 0)) < 0.01
                        )
                        wp_match = (
                            True
                            if (db_row.wave_period is None and api_wp is None)
                            else abs((db_row.wave_period or 0) - (api_wp or 0)) < 0.01
                        )

                        m_matches = all([wh_match, wd_match, wp_match])
                        if not m_matches:
                            diff_count += 1

                        status = "MATCH" if m_matches else "DIFF"
                        print(
                            f"    [Marine] Hour {idx} [{db_time_str}]: {status} | "
                            f"DB wave_h={db_row.wave_height}m, API wave_h={api_wh}m | "
                            f"DB wave_dir={db_row.wave_direction}°, API wave_dir={api_wd}° | "
                            f"DB wave_per={db_row.wave_period}s, API wave_per={api_wp}s"
                        )

                print(f"  -> Total differences detected for {pt['name']}: {diff_count}")


if __name__ == "__main__":
    asyncio.run(run_live_verification())
