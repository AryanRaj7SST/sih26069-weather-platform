"""Observation Corroboration Engine — orchestrator + persistence.

Evaluates WeatherObservations against WeatherReports and persists
structured corroboration assessments into incident_observation_corroborations.

Safety guarantees:
- Never modifies WeatherReport.verification_status.
- Never modifies WeatherReport.credibility_score.
- Never overwrites human operator decisions (is_human_override = True).
- Idempotent: (report_id, observation_id) uniqueness prevents duplicate rows.
- Re-evaluation updates existing rows deterministically.
- Multiple observations from one station produce one trend signal per station.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from geoalchemy2.functions import ST_Distance, ST_GeogFromWKB
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.intelligence.observation_candidate_generator import (
    ObservationCandidateGenerator,
    observation_candidate_generator,
)
from app.intelligence.observation_scorer import (
    ObservationScorer,
    observation_scorer,
)
from app.intelligence.observation_trend_analyzer import (
    ObservationTrendAnalyzer,
    observation_trend_analyzer,
)
from app.intelligence.schemas import (
    CorroborationAssessment,
    CorroborationResult,
    TrendAnalysisResult,
)
from app.models.category import EventCategory
from app.models.corroboration import IncidentObservationCorroboration
from app.models.observation import WeatherObservation
from app.models.report import WeatherReport

logger = logging.getLogger(__name__)


class ObservationCorroborationEngine:
    """Production engine for observation-incident corroboration assessment.

    Orchestrates:
    1. Candidate generation (spatial + temporal bounds)
    2. Station grouping (one trend per station)
    3. 7-signal scoring
    4. Idempotent persistence with human override protection
    """

    def __init__(
        self,
        candidate_gen: Optional[ObservationCandidateGenerator] = None,
        scorer: Optional[ObservationScorer] = None,
        trend_analyzer: Optional[ObservationTrendAnalyzer] = None,
    ) -> None:
        self.candidate_gen = candidate_gen or observation_candidate_generator
        self.scorer = scorer or observation_scorer
        self.trend_analyzer = trend_analyzer or observation_trend_analyzer

    async def evaluate_and_corroborate(
        self,
        db: AsyncSession,
        incident: WeatherReport,
    ) -> List[CorroborationResult]:
        """Evaluate all candidate observations against an incident.

        Groups candidates by station to ensure one trend per station.
        """
        # Resolve incident category
        cat_code = "OTHER"
        if incident.category_id:
            cat_stmt = select(EventCategory).where(EventCategory.id == incident.category_id)
            cat_res = await db.execute(cat_stmt)
            cat_obj = cat_res.scalar_one_or_none()
            if cat_obj:
                cat_code = cat_obj.category_code

        policy = self.scorer.policy

        # Generate candidates
        candidates, is_truncated = await self.candidate_gen.get_candidates(
            db=db,
            incident_lat=incident.latitude,
            incident_lon=incident.longitude,
            incident_time=incident.occurred_at,
            spatial_radius_meters=policy.spatial_radius_meters,
            time_window_hours=policy.time_window_hours,
            metric_filter=policy.metric_key,
            candidate_limit=settings.CORROBORATION_CANDIDATE_LIMIT,
        )

        if is_truncated:
            logger.warning(
                f"Observation candidate limit reached for incident {incident.id}. "
                f"Some observations may not be evaluated."
            )

        if not candidates:
            return []

        # Group candidates by (source_id, station_code) (one trend per source station)
        station_groups: Dict[Tuple[Optional[uuid.UUID], str], List[WeatherObservation]] = {}
        for obs in candidates:
            station_groups.setdefault((obs.source_id, obs.station_code), []).append(obs)

        results: List[CorroborationResult] = []

        for (source_id, station_code), station_observations in station_groups.items():
            # Pick representative observation: most recent within window
            station_observations.sort(key=lambda o: o.observed_at, reverse=True)
            representative = station_observations[0]

            # Compute trend for this source + station
            trend = await self._compute_station_trend(
                db=db,
                station_code=station_code,
                source_id=str(source_id) if source_id else None,
                anchor_time=incident.occurred_at,
                lookback_hours=policy.trend_lookback_hours,
            )

            # Compute distance
            distance_meters = await self._compute_distance(
                db=db,
                observation=representative,
                incident_lat=incident.latitude,
                incident_lon=incident.longitude,
            )

            # Score
            assessment = self.scorer.score_corroboration(
                incident_id=incident.id,
                observation_id=representative.id,
                incident_category=cat_code,
                incident_lat=incident.latitude,
                incident_lon=incident.longitude,
                incident_time=incident.occurred_at,
                incident_location_name=incident.location_name,
                incident_title=incident.title,
                incident_description=incident.description,
                observation_water_level_m=representative.water_level_m,
                observation_time=representative.observed_at,
                observation_raw_metrics=representative.raw_metrics,
                distance_meters=distance_meters,
                trend=trend,
                source_type="CWC",
            )

            # Persist
            corr_id = await self._persist_corroboration(
                db=db,
                incident_id=incident.id,
                observation_id=representative.id,
                distance_meters=distance_meters,
                time_delta_seconds=assessment.signals.temporal_delta_seconds,
                corroboration_score=assessment.overall_score,
                assessment=assessment,
            )

            results.append(
                CorroborationResult(
                    corroboration_id=corr_id,
                    incident_id=incident.id,
                    observation_id=representative.id,
                    relationship_type=assessment.relationship_type,
                    corroboration_score=assessment.overall_score,
                    is_persisted=corr_id is not None,
                    assessment=assessment,
                )
            )

        return results

    async def evaluate_single_pair(
        self,
        db: AsyncSession,
        incident: WeatherReport,
        observation: WeatherObservation,
    ) -> CorroborationResult:
        """Evaluate a single incident-observation pair (for targeted re-evaluation)."""
        cat_code = "OTHER"
        if incident.category_id:
            cat_stmt = select(EventCategory).where(EventCategory.id == incident.category_id)
            cat_res = await db.execute(cat_stmt)
            cat_obj = cat_res.scalar_one_or_none()
            if cat_obj:
                cat_code = cat_obj.category_code

        policy = self.scorer.policy

        trend = await self._compute_station_trend(
            db=db,
            station_code=observation.station_code,
            source_id=str(observation.source_id) if observation.source_id else None,
            anchor_time=incident.occurred_at,
            lookback_hours=policy.trend_lookback_hours,
        )

        distance_meters = await self._compute_distance(
            db=db,
            observation=observation,
            incident_lat=incident.latitude,
            incident_lon=incident.longitude,
        )

        assessment = self.scorer.score_corroboration(
            incident_id=incident.id,
            observation_id=observation.id,
            incident_category=cat_code,
            incident_lat=incident.latitude,
            incident_lon=incident.longitude,
            incident_time=incident.occurred_at,
            incident_location_name=incident.location_name,
            incident_title=incident.title,
            incident_description=incident.description,
            observation_water_level_m=observation.water_level_m,
            observation_time=observation.observed_at,
            observation_raw_metrics=observation.raw_metrics,
            distance_meters=distance_meters,
            trend=trend,
            source_type="CWC",
        )

        corr_id = await self._persist_corroboration(
            db=db,
            incident_id=incident.id,
            observation_id=observation.id,
            distance_meters=distance_meters,
            time_delta_seconds=assessment.signals.temporal_delta_seconds,
            corroboration_score=assessment.overall_score,
            assessment=assessment,
        )

        return CorroborationResult(
            corroboration_id=corr_id,
            incident_id=incident.id,
            observation_id=observation.id,
            relationship_type=assessment.relationship_type,
            corroboration_score=assessment.overall_score,
            is_persisted=corr_id is not None,
            assessment=assessment,
        )

    # ─────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────

    async def _compute_station_trend(
        self,
        db: AsyncSession,
        station_code: str,
        source_id: Optional[str],
        anchor_time: Optional[datetime],
        lookback_hours: float,
    ) -> TrendAnalysisResult:
        """Compute water level trend for a station."""
        return await self.trend_analyzer.analyze_water_level_trend(
            db=db,
            station_code=station_code,
            source_id=source_id,
            anchor_time=anchor_time,
            lookback_hours=lookback_hours,
        )

    async def _compute_distance(
        self,
        db: AsyncSession,
        observation: WeatherObservation,
        incident_lat: Optional[float],
        incident_lon: Optional[float],
    ) -> Optional[float]:
        """Compute geodesic distance between observation and incident.

        Returns None ONLY if either party genuinely lacks coordinates.
        PostGIS/database execution errors raise an explicit exception.
        """
        if incident_lat is None or incident_lon is None:
            return None

        if observation.geom is None:
            return None

        incident_point = func.ST_SetSRID(func.ST_MakePoint(incident_lon, incident_lat), 4326)
        stmt = select(
            ST_Distance(
                ST_GeogFromWKB(WeatherObservation.geom),
                ST_GeogFromWKB(incident_point),
            )
        ).where(WeatherObservation.id == observation.id)

        result = await db.execute(stmt)
        distance = result.scalar_one_or_none()
        return float(distance) if distance is not None else None

    async def _persist_corroboration(
        self,
        db: AsyncSession,
        incident_id: uuid.UUID,
        observation_id: uuid.UUID,
        distance_meters: Optional[float],
        time_delta_seconds: Optional[int],
        corroboration_score: float,
        assessment: CorroborationAssessment,
    ) -> Optional[uuid.UUID]:
        """Idempotently persist or update a corroboration row with human override protection."""
        # Build assessment dict for JSONB storage
        assessment_dict = assessment.model_dump(mode="json")

        # Check for existing row (unique constraint on report_id + observation_id)
        stmt = select(IncidentObservationCorroboration).where(
            and_(
                IncidentObservationCorroboration.report_id == incident_id,
                IncidentObservationCorroboration.observation_id == observation_id,
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Human override protection
            existing_assessment = existing.corroboration_assessment or {}
            if existing_assessment.get("is_human_override") is True:
                # Record latest automated assessment without overwriting human decision
                existing_assessment["last_automated_assessment"] = assessment_dict
                existing_assessment["last_evaluated_at"] = datetime.now(timezone.utc).isoformat()
                existing.corroboration_assessment = existing_assessment
                existing.updated_at = datetime.now(timezone.utc)
                await db.flush()
                logger.debug(f"Preserved human override for ({incident_id}, {observation_id})")
                return existing.id

            # Normal update
            existing.distance_meters = distance_meters
            existing.time_delta_seconds = time_delta_seconds
            existing.corroboration_score = corroboration_score
            existing.corroboration_assessment = assessment_dict
            existing.updated_at = datetime.now(timezone.utc)
            await db.flush()
            return existing.id

        # New row
        new_row = IncidentObservationCorroboration(
            report_id=incident_id,
            observation_id=observation_id,
            distance_meters=distance_meters,
            time_delta_seconds=time_delta_seconds,
            corroboration_score=corroboration_score,
            corroboration_assessment=assessment_dict,
        )
        db.add(new_row)
        await db.flush()
        return new_row.id


observation_corroboration_engine = ObservationCorroborationEngine()
