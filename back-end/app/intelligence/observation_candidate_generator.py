"""Index-assisted candidate generation for observation corroboration.

Uses PostGIS ST_DWithin for spatial bounds and temporal filtering.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, List, Optional, Tuple

from geoalchemy2.functions import ST_DWithin, ST_GeogFromWKB
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.observation import WeatherObservation

logger = logging.getLogger(__name__)


class ObservationCandidateGenerator:
    """Generate observation candidates for corroboration against an incident.

    Uses PostGIS spatial index and temporal bounds to efficiently identify
    nearby, temporally relevant observations.
    """

    async def get_candidates(
        self,
        db: AsyncSession,
        incident_lat: Optional[float],
        incident_lon: Optional[float],
        incident_time: Optional[datetime],
        spatial_radius_meters: float = 35000.0,
        time_window_hours: float = 24.0,
        metric_filter: str = "water_level_m",
        candidate_limit: int = 50,
    ) -> Tuple[List[WeatherObservation], bool]:
        """Retrieve candidate observations within spatial and temporal bounds.

        Args:
            db: Async database session.
            incident_lat: Incident latitude (None if unresolved).
            incident_lon: Incident longitude (None if unresolved).
            incident_time: Incident occurrence time (None if missing).
            spatial_radius_meters: Max distance for spatial filter.
            time_window_hours: Max temporal window for filtering.
            metric_filter: Which metric column must be non-null.
            candidate_limit: Max candidates to return.

        Returns:
            Tuple of (candidate list, is_truncated flag).
        """
        conditions: List[Any] = []

        # Metric availability filter
        if metric_filter == "water_level_m":
            conditions.append(WeatherObservation.water_level_m.isnot(None))
        elif metric_filter == "rainfall_mm":
            conditions.append(WeatherObservation.rainfall_mm.isnot(None))
        elif metric_filter == "temperature_c":
            conditions.append(WeatherObservation.temperature_c.isnot(None))
        else:
            conditions.append(WeatherObservation.water_level_m.isnot(None))

        # Spatial filter (only if coordinates available)
        has_spatial = incident_lat is not None and incident_lon is not None
        if has_spatial:
            incident_point = func.ST_SetSRID(func.ST_MakePoint(incident_lon, incident_lat), 4326)
            conditions.append(
                ST_DWithin(
                    ST_GeogFromWKB(WeatherObservation.geom),
                    ST_GeogFromWKB(incident_point),
                    spatial_radius_meters,
                )
            )

        # Temporal filter (only if incident time available)
        if incident_time is not None:
            time_delta = timedelta(hours=time_window_hours)
            conditions.append(WeatherObservation.observed_at >= (incident_time - time_delta))
            conditions.append(WeatherObservation.observed_at <= (incident_time + time_delta))

        stmt = (
            select(WeatherObservation)
            .distinct(WeatherObservation.source_id, WeatherObservation.station_code)
            .where(and_(*conditions))
            .order_by(
                WeatherObservation.source_id,
                WeatherObservation.station_code,
                WeatherObservation.observed_at.desc(),
            )
            .limit(candidate_limit + 1)  # +1 to detect truncation
        )

        result = await db.execute(stmt)
        candidates = list(result.scalars().all())

        is_truncated = len(candidates) > candidate_limit
        if is_truncated:
            candidates = candidates[:candidate_limit]

        logger.debug(
            f"Observation candidate generation: found={len(candidates)}, "
            f"truncated={is_truncated}, spatial={has_spatial}, "
            f"metric={metric_filter}"
        )

        return candidates, is_truncated


observation_candidate_generator = ObservationCandidateGenerator()
