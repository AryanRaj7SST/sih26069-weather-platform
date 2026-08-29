"""Observation corroboration scorer with WaterLevelPolicy (v1).

Computes 7 independent signal dimensions and produces structured
CorroborationAssessment with hard gates, context guards, and hazard invariants.

Context Guard:
- Textual mention of a river/basin in the incident text does NOT
  constitute strong station context unless the incident's RESOLVED
  location_name explicitly references that river/basin.
- Raw substring match (e.g. "Krishna Nagar") is NOT treated as a river match.
- Same basin with an explicitly different river is classified as WEAK.
- Indirect hazards (HEAVY_RAINFALL, CYCLONE) cannot reach CORROBORATING purely
  from river water level observations.
"""

import logging
import math
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from app.core.config import settings
from app.intelligence.schemas import (
    CorroborationAssessment,
    CorroborationSignalBreakdown,
    ObservationDataQuality,
    ObservationRelationship,
    TrendAnalysisResult,
    TrendDirection,
)

logger = logging.getLogger(__name__)


@dataclass
class WaterLevelPolicy:
    """Metric-specific corroboration policy for CWC water level observations.

    All threshold values are v1 engineering starting defaults — NOT scientifically
    validated parameters.
    """

    metric_key: str = "water_level_m"
    spatial_radius_meters: float = 35000.0
    time_window_hours: float = 24.0
    trend_lookback_hours: float = 6.0
    freshness_max_hours: float = 48.0
    temporal_prior_full_hours: float = 4.0
    temporal_post_decay_rate: float = 0.7
    corroborating_threshold: float = 0.70
    consistent_threshold: float = 0.45
    weak_threshold: float = 0.25
    policy_version: str = "water_level_v1"

    # DIRECT physical relevance: can reach CORROBORATING when strong physical evidence is present
    direct_hazards: Set[str] = field(
        default_factory=lambda: {
            "FLOOD_WATERLOGGING",
            "URBAN_FLOOD",
        }
    )
    # INDIRECT / contextual relevance: cannot reach CORROBORATING solely from water level
    indirect_hazards: Set[str] = field(
        default_factory=lambda: {
            "HEAVY_RAINFALL",
            "CYCLONE",
        }
    )
    # INCOMPATIBLE hazards: hard gate → IRRELEVANT
    incompatible_hazards: Set[str] = field(
        default_factory=lambda: {
            "HEATWAVE",
            "DROUGHT",
            "COLDWAVE",
            "LIGHTNING",
            "THUNDERSTORM",
        }
    )

    @classmethod
    def from_settings(cls) -> "WaterLevelPolicy":
        """Create policy from application settings."""
        return cls(
            spatial_radius_meters=settings.CORROBORATION_WL_SPATIAL_RADIUS_METERS,
            time_window_hours=settings.CORROBORATION_WL_TIME_WINDOW_HOURS,
            trend_lookback_hours=settings.CORROBORATION_WL_TREND_LOOKBACK_HOURS,
            freshness_max_hours=settings.CORROBORATION_WL_FRESHNESS_MAX_HOURS,
            temporal_prior_full_hours=settings.CORROBORATION_WL_TEMPORAL_PRIOR_FULL_HOURS,
            temporal_post_decay_rate=settings.CORROBORATION_WL_TEMPORAL_POST_DECAY_RATE,
            corroborating_threshold=settings.CORROBORATION_WL_CORROBORATING_THRESHOLD,
            consistent_threshold=settings.CORROBORATION_WL_CONSISTENT_THRESHOLD,
            weak_threshold=settings.CORROBORATION_WL_WEAK_THRESHOLD,
        )


class ObservationScorer:
    """Score observation-incident corroboration with 7 independent signals.

    Hard gates:
    - metric_relevance_score == 0.0 → IRRELEVANT (incompatible hazard)
    - data_quality_score == 0.0 → INSUFFICIENT_DATA
    - temporal_score == 0.0 (when timestamps present and delta > window) → IRRELEVANT
    - spatial_score == 0.0 (when coordinates present and distance >= radius) → IRRELEVANT
    - missing coordinates with weak/no river context → INSUFFICIENT_DATA
    """

    SOURCE_TRUST_MAP: Dict[str, float] = {
        "CWC_NWDP": 0.92,
        "CWC": 0.92,
    }

    def __init__(self, policy: Optional[WaterLevelPolicy] = None) -> None:
        self.policy = policy or WaterLevelPolicy.from_settings()

    # ─────────────────────────────────────────────────────
    # 1. Spatial Score
    # ─────────────────────────────────────────────────────
    def compute_spatial_score(
        self,
        distance_meters: Optional[float],
    ) -> Optional[float]:
        """Linear decay from 1.0 at 0m to 0.0 at spatial_radius_meters.

        Returns None if distance is not available (missing coordinates).
        """
        if distance_meters is None:
            return None

        if distance_meters < 0:
            return None

        if distance_meters >= self.policy.spatial_radius_meters:
            return 0.0

        return round(1.0 - (distance_meters / self.policy.spatial_radius_meters), 4)

    # ─────────────────────────────────────────────────────
    # 2. Temporal Score (Asymmetric)
    # ─────────────────────────────────────────────────────
    def compute_temporal_score(
        self,
        observation_time: Optional[datetime],
        incident_time: Optional[datetime],
    ) -> Optional[float]:
        """Asymmetric temporal decay for water level observations.

        Prior observations (before incident): full score within prior_full_hours.
        Concurrent (±30 min): full score.
        Post observations (after incident): decaying score.

        Returns None if either timestamp is missing.
        """
        if observation_time is None or incident_time is None:
            return None

        delta_seconds = (observation_time - incident_time).total_seconds()
        delta_hours = abs(delta_seconds) / 3600.0

        # Beyond configured window → 0.0
        if delta_hours > self.policy.time_window_hours:
            return 0.0

        # Concurrent (±30 min)
        if abs(delta_seconds) <= 1800:
            return 1.0

        # Prior observation (observation BEFORE incident → delta_seconds < 0)
        if delta_seconds < 0:
            prior_hours = abs(delta_seconds) / 3600.0
            if prior_hours <= self.policy.temporal_prior_full_hours:
                return 1.0
            # Linear decay from full_hours to window
            remaining = self.policy.time_window_hours - self.policy.temporal_prior_full_hours
            if remaining <= 0:
                return 0.0
            decay = 1.0 - ((prior_hours - self.policy.temporal_prior_full_hours) / remaining)
            return round(max(0.0, decay), 4)

        # Post observation (observation AFTER incident → delta_seconds > 0)
        post_hours = delta_seconds / 3600.0
        decay_rate = self.policy.temporal_post_decay_rate
        score = decay_rate ** (post_hours / self.policy.time_window_hours * 3.0)
        return round(max(0.0, min(1.0, score)), 4)

    # ─────────────────────────────────────────────────────
    # 3. Metric Relevance Score
    # ─────────────────────────────────────────────────────
    def compute_metric_relevance(self, incident_category: str) -> float:
        """Check if water_level_m is relevant to the incident's hazard category.

        Direct hazards (FLOOD_WATERLOGGING) → 1.0
        Indirect hazards (HEAVY_RAINFALL, CYCLONE) → 0.55
        Incompatible hazards (HEATWAVE, DROUGHT, etc.) → 0.0
        """
        clean_cat = (incident_category or "OTHER").strip().upper()

        if clean_cat in self.policy.incompatible_hazards:
            return 0.0

        if clean_cat in self.policy.direct_hazards:
            return 1.0

        if clean_cat in self.policy.indirect_hazards:
            return 0.55

        # Unknown/OTHER category: moderate relevance
        return 0.30

    # ─────────────────────────────────────────────────────
    # 4. Station Context Score (with Context Guard & Substring Safety)
    # ─────────────────────────────────────────────────────
    def compute_station_context_score(
        self,
        observation_raw_metrics: Optional[Dict[str, Any]],
        incident_location_name: Optional[str],
        incident_title: Optional[str],
        incident_description: Optional[str],
    ) -> float:
        """Compute station context compatibility with explicit context guard.

        Context Guard:
        - ONLY incident_location_name provides STRONG context (explicit association).
        - Raw substring matches (e.g. 'Krishna Nagar') are guarded and not treated as rivers.
        - Same basin but explicitly different rivers → weak (0.20).
        - Same basin, river unknown / unstated → moderate (0.50).
        - Title mention → weak (0.35–0.40).
        - Description mention → generic/minimal (0.20).
        - State-only match → weak (0.20).
        - No context → 0.10.
        """
        if not observation_raw_metrics:
            return 0.10

        station_river = _normalize_name(observation_raw_metrics.get("river"))
        station_basin = _normalize_name(observation_raw_metrics.get("basin"))
        station_tributary = _normalize_name(observation_raw_metrics.get("tributary"))
        station_local_river = _normalize_name(observation_raw_metrics.get("local_river"))
        station_district = _normalize_name(observation_raw_metrics.get("district"))
        station_state = _normalize_name(observation_raw_metrics.get("state"))

        station_river_names = set()
        for name in [station_river, station_tributary, station_local_river]:
            if name:
                station_river_names.add(name)

        loc_name_norm = _normalize_name(incident_location_name)
        title_norm = _normalize_name(incident_title)
        desc_norm = _normalize_name(incident_description)

        # === 1. STRONG CONTEXT: Explicit River in location_name ===
        if loc_name_norm:
            for river_name in station_river_names:
                if river_name and _is_river_entity_mention(loc_name_norm, river_name):
                    return 1.0

        # === 2. Basin in location_name ===
        if loc_name_norm and station_basin:
            # Check if incident explicitly names a DIFFERENT river in the same basin
            is_different_river = False
            if "river" in loc_name_norm or "nadi" in loc_name_norm:
                has_station_river = any(
                    _is_river_entity_mention(loc_name_norm, r) for r in station_river_names
                )
                if not has_station_river:
                    is_different_river = True

            if is_different_river:
                # Same basin but explicitly different river → weak (0.15)
                return 0.15

            if _is_river_entity_mention(loc_name_norm, station_basin):
                # Same basin, river unknown / unstated in incident → moderate (0.50)
                return 0.50

        # === 3. District in location_name ===
        if loc_name_norm and station_district and station_district in loc_name_norm:
            # Check for localized street waterlogging / drainage issue (not river)
            combined = f"{loc_name_norm} {title_norm or ''} {desc_norm or ''}"
            if any(w in combined for w in ["street", "drain", "subway", "underpass"]):
                return 0.20

            # If river is in title -> 0.55
            for river_name in station_river_names:
                if river_name and title_norm and _is_river_entity_mention(title_norm, river_name):
                    return 0.55
            return 0.50

        # === 4. River/basin in title (partial association) ===
        if title_norm:
            for river_name in station_river_names:
                if river_name and _is_river_entity_mention(title_norm, river_name):
                    return 0.40

            if station_basin and _is_river_entity_mention(title_norm, station_basin):
                return 0.35

        # === 5. State match ===
        if station_state:
            if loc_name_norm and station_state in loc_name_norm:
                return 0.20
            if title_norm and station_state in title_norm:
                return 0.20

        # === 6. Generic description mention ===
        if desc_norm:
            for river_name in station_river_names:
                if river_name and _is_river_entity_mention(desc_norm, river_name):
                    return 0.20

            if station_basin and _is_river_entity_mention(desc_norm, station_basin):
                return 0.20

        # No context established
        return 0.10

    # ─────────────────────────────────────────────────────
    # 5. Data Quality Score
    # ─────────────────────────────────────────────────────
    def assess_data_quality(
        self,
        water_level_m: Optional[float],
        observation_time: Optional[datetime],
        incident_time: Optional[datetime],
    ) -> tuple[ObservationDataQuality, float]:
        """Assess observation data quality and return (quality_enum, score).

        Returns score=0.0 for hard-gate conditions (MISSING_METRIC, MALFORMED).
        Validates finite numeric values without arbitrary universal elevation limits.
        """
        # Missing metric
        if water_level_m is None:
            return ObservationDataQuality.MISSING_METRIC, 0.0

        # Validate finite numeric value (reject NaN, Inf, non-numeric types)
        try:
            val = float(water_level_m)
            if not math.isfinite(val) or math.isnan(val):
                return ObservationDataQuality.MALFORMED, 0.0
        except (ValueError, TypeError):
            return ObservationDataQuality.MALFORMED, 0.0

        # Staleness check
        if observation_time is not None and incident_time is not None:
            delta_hours = abs((observation_time - incident_time).total_seconds()) / 3600.0
            if delta_hours > self.policy.freshness_max_hours:
                return ObservationDataQuality.STALE, 0.1

        return ObservationDataQuality.VALID, 1.0

    # ─────────────────────────────────────────────────────
    # 6. Source Trust Score
    # ─────────────────────────────────────────────────────
    def compute_source_trust(self, source_code: Optional[str] = None) -> float:
        """Return institutional trust score for the observation source.

        v1 supports CWC River Telemetry (NWDP).
        """
        if not source_code:
            return settings.CORROBORATION_CWC_SOURCE_TRUST
        return self.SOURCE_TRUST_MAP.get(
            source_code.upper(), settings.CORROBORATION_CWC_SOURCE_TRUST
        )

    # ─────────────────────────────────────────────────────
    # 7. Composite Score + Classification
    # ─────────────────────────────────────────────────────
    def score_corroboration(
        self,
        incident_id: uuid.UUID,
        observation_id: uuid.UUID,
        incident_category: str,
        incident_lat: Optional[float],
        incident_lon: Optional[float],
        incident_time: Optional[datetime],
        incident_location_name: Optional[str],
        incident_title: Optional[str],
        incident_description: Optional[str],
        observation_water_level_m: Optional[float],
        observation_time: Optional[datetime],
        observation_raw_metrics: Optional[Dict[str, Any]],
        distance_meters: Optional[float],
        trend: Optional[TrendAnalysisResult],
        source_type: Optional[str] = "CWC",
    ) -> CorroborationAssessment:
        """Compute full 7-signal corroboration assessment with hardened invariants."""
        # Individual signals
        spatial_score = self.compute_spatial_score(distance_meters)
        temporal_score = self.compute_temporal_score(observation_time, incident_time)
        metric_relevance = self.compute_metric_relevance(incident_category)
        station_context = self.compute_station_context_score(
            observation_raw_metrics,
            incident_location_name,
            incident_title,
            incident_description,
        )
        data_quality_enum, data_quality_score = self.assess_data_quality(
            observation_water_level_m,
            observation_time,
            incident_time,
        )
        source_trust = self.compute_source_trust(source_type)

        # Trend score
        from app.intelligence.observation_trend_analyzer import ObservationTrendAnalyzer

        trend_analyzer = ObservationTrendAnalyzer()
        trend_score = trend_analyzer.compute_trend_score(trend) if trend else 0.0

        # Build signal breakdown
        time_delta_seconds: Optional[int] = None
        if observation_time is not None and incident_time is not None:
            time_delta_seconds = int((observation_time - incident_time).total_seconds())

        signals = CorroborationSignalBreakdown(
            spatial_distance_meters=distance_meters,
            spatial_score=spatial_score,
            temporal_delta_seconds=time_delta_seconds,
            temporal_score=temporal_score,
            metric_relevance_score=metric_relevance,
            station_context_score=station_context,
            trend_score=trend_score,
            data_quality_score=data_quality_score,
            source_trust_score=source_trust,
        )

        # ─── Hard gate checks ───

        # Gate 1: Incompatible hazard
        if metric_relevance == 0.0:
            return self._build_assessment(
                incident_id=incident_id,
                observation_id=observation_id,
                relationship=ObservationRelationship.IRRELEVANT,
                score=0.0,
                signals=signals,
                trend=trend,
                data_quality=data_quality_enum,
                explanation=(
                    f"Water level metric is incompatible with incident category "
                    f"'{incident_category}'. No corroboration possible."
                ),
            )

        # Gate 2: Data quality (missing metric or malformed)
        if data_quality_score == 0.0:
            quality_reason = {
                ObservationDataQuality.MISSING_METRIC: "water_level_m is NULL",
                ObservationDataQuality.MALFORMED: "water_level_m is outside valid range",
            }.get(data_quality_enum, "data quality issue")
            return self._build_assessment(
                incident_id=incident_id,
                observation_id=observation_id,
                relationship=ObservationRelationship.INSUFFICIENT_DATA,
                score=0.0,
                signals=signals,
                trend=trend,
                data_quality=data_quality_enum,
                explanation=f"Observation data quality insufficient: {quality_reason}.",
            )

        # Gate 3: Staleness
        if data_quality_enum == ObservationDataQuality.STALE:
            return self._build_assessment(
                incident_id=incident_id,
                observation_id=observation_id,
                relationship=ObservationRelationship.IRRELEVANT,
                score=0.05,
                signals=signals,
                trend=trend,
                data_quality=data_quality_enum,
                explanation="Observation is stale (beyond freshness window). Not usable.",
            )

        # Gate 4: Temporal gap (> 24h window)
        if temporal_score == 0.0 and observation_time is not None and incident_time is not None:
            return self._build_assessment(
                incident_id=incident_id,
                observation_id=observation_id,
                relationship=ObservationRelationship.IRRELEVANT,
                score=0.0,
                signals=signals,
                trend=trend,
                data_quality=data_quality_enum,
                explanation=(
                    "Observation occurred outside the maximum temporal window. "
                    "Classified as IRRELEVANT."
                ),
            )

        # Gate 5: Spatial gap (> 35km radius)
        if spatial_score == 0.0 and distance_meters is not None:
            return self._build_assessment(
                incident_id=incident_id,
                observation_id=observation_id,
                relationship=ObservationRelationship.IRRELEVANT,
                score=0.0,
                signals=signals,
                trend=trend,
                data_quality=data_quality_enum,
                explanation=(
                    "Observation station is beyond maximum spatial radius. "
                    "Classified as IRRELEVANT."
                ),
            )

        # Gate 6: Missing coordinates with weak/no river context → INSUFFICIENT_DATA
        if spatial_score is None and station_context <= 0.20:
            return self._build_assessment(
                incident_id=incident_id,
                observation_id=observation_id,
                relationship=ObservationRelationship.INSUFFICIENT_DATA,
                score=0.20,
                signals=signals,
                trend=trend,
                data_quality=data_quality_enum,
                explanation=(
                    "Incident has no safely resolved coordinates — "
                    "spatial proximity cannot be confirmed."
                ),
            )

        # Gate 7: Distant + no context → IRRELEVANT
        if station_context <= 0.20 and (spatial_score is not None and spatial_score < 0.10):
            return self._build_assessment(
                incident_id=incident_id,
                observation_id=observation_id,
                relationship=ObservationRelationship.IRRELEVANT,
                score=0.10,
                signals=signals,
                trend=trend,
                data_quality=data_quality_enum,
                explanation=(
                    "Observation is from an unrelated river/basin and distant from incident area."
                ),
            )

        # ─── Contradictory check (Conservative & Authoritative) ───
        is_contradictory = self._check_contradictory(
            observation_water_level_m=observation_water_level_m,
            observation_raw_metrics=observation_raw_metrics,
            station_context=station_context,
            spatial_score=spatial_score,
            temporal_score=temporal_score,
            trend=trend,
            data_quality_enum=data_quality_enum,
            incident_title=incident_title,
            incident_description=incident_description,
        )

        if is_contradictory:
            return self._build_assessment(
                incident_id=incident_id,
                observation_id=observation_id,
                relationship=ObservationRelationship.CONTRADICTORY,
                score=0.50,
                signals=signals,
                trend=trend,
                data_quality=data_quality_enum,
                explanation=self._build_contradictory_explanation(
                    observation_raw_metrics,
                    trend,
                    distance_meters,
                ),
            )

        # ─── Composite score computation ───
        eff_spatial = spatial_score if spatial_score is not None else 0.0
        eff_temporal = temporal_score if temporal_score is not None else 0.0

        composite = (
            eff_spatial * 0.20
            + eff_temporal * 0.15
            + metric_relevance * 0.15
            + station_context * 0.20
            + trend_score * 0.20
            + data_quality_score * 0.05
            + source_trust * 0.05
        )
        composite = round(min(1.0, max(0.0, composite)), 4)

        # ─── Gating & Caps ───
        context_capped = False
        if spatial_score is None:
            # Missing coordinates → cap at WEAK (0.35)
            composite = min(composite, 0.35)
        elif station_context <= 0.15:
            # Very weak context → cap at WEAK (0.35)
            composite = min(composite, 0.35)
            context_capped = True
        elif station_context == 0.20:
            # State-level match, weak district, or different river in same basin
            is_rising = trend is not None and trend.direction == TrendDirection.RISING
            if (spatial_score is not None and spatial_score >= 0.40) and is_rising:
                composite = min(composite, 0.48)
            else:
                composite = min(composite, 0.35)
        elif station_context <= 0.55:
            # District/title/basin context without direct river match in location_name
            is_distant_or_single = (spatial_score is not None and spatial_score < 0.40) or (
                trend is not None and trend.points_count <= 1
            )
            if is_distant_or_single:
                composite = min(composite, 0.35)
            else:
                composite = min(composite, 0.60)
        elif trend is None or trend.direction != TrendDirection.RISING or trend.points_count < 2:
            # Same river/basin but single point or steady/falling → cap at CONSISTENT (0.60)
            composite = min(composite, 0.60)

        # ─── HARD INVARIANT: Indirect Hazards cannot reach CORROBORATING ───
        clean_cat = (incident_category or "OTHER").strip().upper()
        if clean_cat not in self.policy.direct_hazards:
            max_allowed = self.policy.corroborating_threshold - 0.01  # 0.69 max
            if composite > max_allowed:
                composite = round(max_allowed, 4)

        # ─── Classification ───
        relationship = self._classify(composite)

        # Build explanation
        explanation = self._build_explanation(
            relationship=relationship,
            composite=composite,
            signals=signals,
            trend=trend,
            observation_raw_metrics=observation_raw_metrics,
            distance_meters=distance_meters,
            incident_location_name=incident_location_name,
            spatial_score=spatial_score,
            context_capped=context_capped,
        )

        return self._build_assessment(
            incident_id=incident_id,
            observation_id=observation_id,
            relationship=relationship,
            score=composite,
            signals=signals,
            trend=trend,
            data_quality=data_quality_enum,
            explanation=explanation,
        )

    def _check_contradictory(
        self,
        observation_water_level_m: Optional[float],
        observation_raw_metrics: Optional[Dict[str, Any]],
        station_context: float,
        spatial_score: Optional[float],
        temporal_score: Optional[float],
        trend: Optional[TrendAnalysisResult],
        data_quality_enum: ObservationDataQuality,
        incident_title: Optional[str],
        incident_description: Optional[str],
    ) -> bool:
        """Check if observation directly and authoritatively CONTRADICTS the incident claim.

        Contradictory requires ALL conditions:
        1. Observation is VALID
        2. Strong station context (context >= 0.70, explicit same river)
        3. Spatially close (spatial_score >= 0.90, <= 3500m)
        4. Temporally concurrent (temporal_score >= 0.90, within 1h)
        5. Trend has >= 5 readings with steady/falling delta and zero gaps
        6. Authoritative contradiction signal:
           - Station raw_metrics has danger_level or warning_level, AND observed water level
             is well below warning level (e.g. observed < warning_level - 1.0), while incident
             claims river level breached danger/warning level / overflowing banks.
           - OR explicit authoritative contradiction flag is present in telemetry.
        """
        if data_quality_enum != ObservationDataQuality.VALID:
            return False

        if station_context < 0.70:
            return False

        if spatial_score is None or spatial_score < 0.90:
            return False

        if temporal_score is None or temporal_score < 0.90:
            return False

        if (
            trend is None
            or trend.direction not in (TrendDirection.STEADY, TrendDirection.FALLING)
            or trend.points_count < 5
            or trend.has_data_gaps
            or (trend.delta_value is not None and abs(trend.delta_value) > 0.02)
        ):
            return False

        # Authoritative threshold check in raw_metrics
        if observation_raw_metrics and observation_water_level_m is not None:
            danger_level = observation_raw_metrics.get(
                "danger_level"
            ) or observation_raw_metrics.get("warning_level")
            if danger_level is not None:
                try:
                    threshold = float(str(danger_level))
                    # If observed water level is at least 1.0m below danger level
                    if observation_water_level_m < (threshold - 1.0):
                        combined_text = (
                            f"{incident_title or ''} {incident_description or ''}"
                        ).lower()
                        if any(
                            kw in combined_text
                            for kw in [
                                "overflowing",
                                "danger level",
                                "breached",
                                "flood emergency",
                                "catastrophic",
                            ]
                        ):
                            return True
                except (ValueError, TypeError):
                    pass

            if observation_raw_metrics.get("is_authoritative_contradiction") is True:
                return True

        return False

    def _classify(self, composite: float) -> ObservationRelationship:
        """Classify composite score into relationship type."""
        if composite >= self.policy.corroborating_threshold:
            return ObservationRelationship.CORROBORATING
        if composite >= self.policy.consistent_threshold:
            return ObservationRelationship.CONSISTENT
        if composite >= self.policy.weak_threshold:
            return ObservationRelationship.WEAK
        return ObservationRelationship.IRRELEVANT

    def _build_assessment(
        self,
        incident_id: uuid.UUID,
        observation_id: uuid.UUID,
        relationship: ObservationRelationship,
        score: float,
        signals: CorroborationSignalBreakdown,
        trend: Optional[TrendAnalysisResult],
        data_quality: ObservationDataQuality,
        explanation: str,
    ) -> CorroborationAssessment:
        """Create a CorroborationAssessment with standard metadata."""
        return CorroborationAssessment(
            incident_id=incident_id,
            observation_id=observation_id,
            relationship_type=relationship,
            overall_score=score,
            signals=signals,
            trend=trend,
            data_quality=data_quality,
            explanation=explanation,
            engine_version=settings.CORROBORATION_ENGINE_VERSION,
            policy_version=self.policy.policy_version,
            metric_type=self.policy.metric_key,
            assessed_at=datetime.now(timezone.utc),
            is_human_override=False,
        )

    def _build_explanation(
        self,
        relationship: ObservationRelationship,
        composite: float,
        signals: CorroborationSignalBreakdown,
        trend: Optional[TrendAnalysisResult],
        observation_raw_metrics: Optional[Dict[str, Any]],
        distance_meters: Optional[float],
        incident_location_name: Optional[str],
        spatial_score: Optional[float],
        context_capped: bool,
    ) -> str:
        """Build human-readable explanation text."""
        parts: list[str] = []
        station_name = ""
        basin_name = ""
        if observation_raw_metrics:
            station_name = observation_raw_metrics.get("river", "") or ""
            basin_name = observation_raw_metrics.get("basin", "") or ""

        # Spatial context
        if distance_meters is not None:
            parts.append(f"CWC observation {distance_meters / 1000:.1f} km from incident area")
        else:
            parts.append("CWC observation with no confirmed spatial proximity")

        # Basin/river context
        if basin_name:
            parts.append(f"in {basin_name} basin")
        if station_name:
            parts.append(f"on {station_name} river")

        # Trend
        if trend and trend.direction not in (
            TrendDirection.INSUFFICIENT_DATA,
            TrendDirection.SINGLE_POINT,
        ):
            direction_text = trend.direction.value.lower()
            if trend.delta_value is not None:
                parts.append(
                    f"Water level {direction_text} by {abs(trend.delta_value):.2f} m "
                    f"over {(trend.span_minutes or 0) / 60:.1f} h "
                    f"({trend.points_count} readings)"
                )
            else:
                parts.append(f"Water level trend: {direction_text}")
        elif trend and trend.direction == TrendDirection.SINGLE_POINT:
            parts.append("Single observation available (no trend)")

        # Context cap warning
        if context_capped:
            parts.append("Station context is weak — capped below corroborating threshold")

        # Missing coordinates
        if spatial_score is None:
            parts.append(
                "Incident has no safely resolved coordinates — "
                "spatial proximity cannot be confirmed"
            )

        return ". ".join(parts) + "."

    def _build_contradictory_explanation(
        self,
        observation_raw_metrics: Optional[Dict[str, Any]],
        trend: Optional[TrendAnalysisResult],
        distance_meters: Optional[float],
    ) -> str:
        """Build explanation for CONTRADICTORY classification."""
        parts = ["CONTRADICTORY assessment"]
        if observation_raw_metrics:
            river = observation_raw_metrics.get("river", "")
            if river:
                parts.append(f"Same-river CWC station ({river})")
        if distance_meters is not None:
            parts.append(f"{distance_meters / 1000:.1f} km from incident")
        if trend:
            direction = trend.direction.value.lower()
            parts.append(
                f"shows {direction} water level "
                f"({trend.points_count} readings over "
                f"{(trend.span_minutes or 0) / 60:.1f} h)"
            )
        parts.append(
            "Authoritative hydrological observation directly conflicts "
            "with reported flood emergency"
        )
        return ". ".join(parts) + "."


def _is_river_entity_mention(text: Optional[str], river_name: Optional[str]) -> bool:
    """Check whether text refers specifically to the river, guarding against raw substring matches.

    Example:
    - "Krishna River", "River Krishna", "along the Krishna", "Krishna bank" -> True
    - "Krishna Nagar", "Krishna Colony", "Krishna Layout", "Krishna Marg" -> False
    """
    if not text or not river_name:
        return False

    text_norm = str(text).strip().lower()
    river_norm = str(river_name).strip().lower()

    if not text_norm or not river_norm:
        return False

    # Check if river_norm appears as a whole word / phrase
    pattern = r"\b" + re.escape(river_norm) + r"\b"
    match = re.search(pattern, text_norm)
    if not match:
        return False

    # Locality suffixes that indicate an urban settlement, road, or building rather than a river
    locality_suffixes = [
        "nagar",
        "colony",
        "layout",
        "road",
        "rd",
        "marg",
        "street",
        "st",
        "lane",
        "gali",
        "enclave",
        "vihar",
        "apartment",
        "apartments",
        "society",
        "complex",
        "building",
        "bhavan",
        "puram",
        "pally",
        "hall",
        "hotel",
        "ward",
    ]

    # River indicator keywords that confirm river context
    river_indicators = [
        "river",
        "nadi",
        "stream",
        "basin",
        "bank",
        "banks",
        "ghat",
        "bridge",
        "dam",
        "barrage",
        "catchment",
        "overflow",
        "water level",
    ]

    # If any explicit river indicator appears near or in text, it's a river mention
    for ind in river_indicators:
        if ind in text_norm:
            return True

    # Check what word follows river_norm
    after_match = text_norm[match.end() :].strip()
    next_word_match = re.match(r"^[^\w]*(\w+)", after_match)
    if next_word_match:
        next_word = next_word_match.group(1).lower()
        if next_word in locality_suffixes:
            # Suffix indicates a locality/street, not the river itself
            return False

    # Also check what word precedes river_norm
    before_match = text_norm[: match.start()].strip()
    prev_word_match = re.search(r"(\w+)[^\w]*$", before_match)
    if prev_word_match:
        prev_word = prev_word_match.group(1).lower()
        if prev_word in ["hotel", "shri", "sri", "lord", "temple", "mandir"]:
            return False

    return True


def _normalize_name(value: Any) -> Optional[str]:
    """Normalize a name string for comparison: lowercase, stripped, collapsed whitespace."""
    if value is None:
        return None
    s = str(value).strip().lower()
    s = re.sub(r"\s+", " ", s)
    if not s or s in ("-", "na", "n/a", "null", "none", "unknown"):
        return None
    return s


observation_scorer = ObservationScorer()
