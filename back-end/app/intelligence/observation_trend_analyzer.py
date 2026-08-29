"""Same-station-same-metric trend analyzer for observation corroboration.

Computes trend direction (RISING/STEADY/FALLING/SINGLE_POINT/INSUFFICIENT_DATA)
from sequential observations at a single station. Never mixes stations or metrics.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.schemas import TrendAnalysisResult, TrendDirection
from app.models.observation import WeatherObservation

logger = logging.getLogger(__name__)

# Minimum absolute change to classify as RISING or FALLING (meters).
# Below this, classify as STEADY to avoid noise sensitivity.
_WATER_LEVEL_STEADY_THRESHOLD_M = 0.05


class ObservationTrendAnalyzer:
    """Compute metric trends from same-station sequential observations.

    Safety invariants:
    - Only queries observations from the SAME station_code.
    - Only queries observations from the SAME source_id.
    - Only uses a single metric column per analysis.
    - Multiple observations from one station produce ONE trend signal.
    """

    async def analyze_water_level_trend(
        self,
        db: AsyncSession,
        station_code: str,
        source_id: "str | None",
        anchor_time: Optional[datetime],
        lookback_hours: float = 6.0,
        expected_interval_minutes: float = 60.0,
    ) -> TrendAnalysisResult:
        """Compute water level trend from sequential readings at a single station.

        Args:
            db: Async database session.
            station_code: CWC station code (e.g., "CWC-KRISHNA-YADGIR").
            source_id: Source UUID string to constrain to same source (optional).
            anchor_time: Reference time for lookback window (None if incident has no timestamp).
            lookback_hours: How far back to query.
            expected_interval_minutes: Expected reporting interval for gap detection.

        Returns:
            TrendAnalysisResult with direction, delta, rate, and quality flags.
        """
        metric_key = "water_level_m"

        if anchor_time is None:
            return TrendAnalysisResult(
                direction=TrendDirection.INSUFFICIENT_DATA,
                points_count=0,
                metric_key=metric_key,
                station_code=station_code,
            )

        start_time = anchor_time - timedelta(hours=lookback_hours)

        # Build query: same station, same metric, within lookback window
        conditions = [
            WeatherObservation.station_code == station_code,
            WeatherObservation.observed_at >= start_time,
            WeatherObservation.observed_at <= anchor_time,
            WeatherObservation.water_level_m.isnot(None),
        ]

        if source_id:
            conditions.append(cast(WeatherObservation.source_id, sa_text_type()) == source_id)

        stmt = (
            select(
                WeatherObservation.observed_at,
                WeatherObservation.water_level_m,
            )
            .where(and_(*conditions))
            .order_by(WeatherObservation.observed_at.asc())
        )

        result = await db.execute(stmt)
        rows = result.all()

        # Deduplicate by timestamp (keep last-inserted / latest value)
        seen_times: dict[datetime, float] = {}
        for row in rows:
            obs_time = row[0]
            wl_value = row[1]
            if wl_value is not None:
                seen_times[obs_time] = wl_value

        points = sorted(seen_times.items(), key=lambda x: x[0])

        if len(points) == 0:
            return TrendAnalysisResult(
                direction=TrendDirection.INSUFFICIENT_DATA,
                points_count=0,
                metric_key=metric_key,
                station_code=station_code,
            )

        if len(points) == 1:
            return TrendAnalysisResult(
                direction=TrendDirection.SINGLE_POINT,
                delta_value=None,
                rate_per_hour=None,
                points_count=1,
                span_minutes=0.0,
                has_data_gaps=False,
                metric_key=metric_key,
                station_code=station_code,
            )

        # Compute trend from multi-point sequence
        first_time, first_val = points[0]
        last_time, last_val = points[-1]

        delta_value = last_val - first_val
        span_seconds = (last_time - first_time).total_seconds()
        span_minutes = span_seconds / 60.0
        rate_per_hour = (delta_value / span_seconds * 3600.0) if span_seconds > 0 else 0.0

        # Gap detection: check if any consecutive pair exceeds 2× expected interval
        has_data_gaps = False
        gap_threshold_seconds = expected_interval_minutes * 60.0 * 2.0
        for i in range(1, len(points)):
            gap = (points[i][0] - points[i - 1][0]).total_seconds()
            if gap > gap_threshold_seconds:
                has_data_gaps = True
                break

        # Direction classification
        if abs(delta_value) < _WATER_LEVEL_STEADY_THRESHOLD_M:
            direction = TrendDirection.STEADY
        elif delta_value > 0:
            direction = TrendDirection.RISING
        else:
            direction = TrendDirection.FALLING

        return TrendAnalysisResult(
            direction=direction,
            delta_value=round(delta_value, 4),
            rate_per_hour=round(rate_per_hour, 4),
            points_count=len(points),
            span_minutes=round(span_minutes, 1),
            has_data_gaps=has_data_gaps,
            metric_key=metric_key,
            station_code=station_code,
        )

    def compute_trend_score(self, trend: TrendAnalysisResult) -> float:
        """Convert a TrendAnalysisResult into a 0.0–1.0 score for water level corroboration.

        Rising trend → higher score (physical evidence of worsening conditions).
        Falling trend → lower score (conditions subsiding).
        Steady → moderate score (no change signal).
        """
        if trend.direction == TrendDirection.INSUFFICIENT_DATA:
            return 0.0

        if trend.direction == TrendDirection.SINGLE_POINT:
            return 0.25  # Weak signal: can't determine direction

        if trend.direction == TrendDirection.STEADY:
            return 0.40  # Neutral: no worsening but conditions are present

        if trend.direction == TrendDirection.RISING:
            # Scale by rate: faster rise = stronger signal, capped at 1.0
            rate = abs(trend.rate_per_hour or 0.0)
            # Baseline 0.6 for any rise, up to 1.0 for rapid rise (≥ 0.5 m/h)
            score = min(1.0, 0.6 + (rate / 0.5) * 0.4)
            return round(score, 4)

        if trend.direction == TrendDirection.FALLING:
            # Falling = conditions subsiding, weak positive signal (aftermath)
            return 0.30

        return 0.0


def sa_text_type():
    """Return SQLAlchemy String type for UUID casting."""
    from sqlalchemy import String

    return String


observation_trend_analyzer = ObservationTrendAnalyzer()
