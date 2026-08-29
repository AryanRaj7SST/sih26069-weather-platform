import math
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.config import settings
from app.intelligence.category_rules import get_category_compatibility
from app.intelligence.resolver import location_resolver
from app.intelligence.schemas import (
    DuplicateAssessment,
    DuplicateDecision,
    DuplicateSignalBreakdown,
)
from app.intelligence.semantic_similarity import semantic_vectorizer


class DuplicateScorer:
    """Multi-signal scoring engine combining spatial, temporal, semantic, and category factors.

    NOTE: Initial thresholds are v1 heuristic policy parameters, not scientifically ground-truth.
    """

    def __init__(
        self,
        max_spatial_radius_meters: Optional[float] = None,
        max_time_window_hours: Optional[float] = None,
        semantic_threshold: Optional[float] = None,
        confirmed_threshold: Optional[float] = None,
        possible_threshold: Optional[float] = None,
        engine_version: Optional[str] = None,
        semantic_method: Optional[str] = None,
    ) -> None:
        self.max_radius = max_spatial_radius_meters or settings.DUPLICATE_SPATIAL_RADIUS_METERS
        self.max_time_seconds = (
            max_time_window_hours or settings.DUPLICATE_TIME_WINDOW_HOURS
        ) * 3600.0
        self.semantic_threshold = semantic_threshold or settings.DUPLICATE_SEMANTIC_THRESHOLD
        self.confirmed_threshold = confirmed_threshold or settings.DUPLICATE_CONFIRMED_THRESHOLD
        self.possible_threshold = possible_threshold or settings.DUPLICATE_POSSIBLE_THRESHOLD
        self.engine_version = engine_version or settings.DUPLICATE_ENGINE_VERSION
        self.semantic_method = semantic_method or settings.DUPLICATE_SEMANTIC_METHOD

    @staticmethod
    def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate great-circle distance between two WGS84 points in meters."""
        r = 6371000.0  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2.0) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    def score_pair(
        self,
        report_a_id: uuid.UUID,
        report_b_id: uuid.UUID,
        title_a: str,
        title_b: str,
        desc_a: Optional[str],
        desc_b: Optional[str],
        cat_a: str,
        cat_b: str,
        lat_a: Optional[float],
        lon_a: Optional[float],
        lat_b: Optional[float],
        lon_b: Optional[float],
        time_a: Optional[datetime],
        time_b: Optional[datetime],
        loc_name_a: Optional[str] = None,
        loc_name_b: Optional[str] = None,
        vec_a: Optional[Any] = None,
        vec_b: Optional[Any] = None,
    ) -> DuplicateAssessment:
        """Evaluate a candidate incident pair across spatial, temporal, and text signals."""
        # 1. Category Compatibility
        cat_score = get_category_compatibility(cat_a, cat_b)

        # 2. Spatial Proximity
        spatial_distance: Optional[float] = None
        spatial_score = 0.0
        if lat_a is not None and lon_a is not None and lat_b is not None and lon_b is not None:
            spatial_distance = self.haversine_distance_meters(lat_a, lon_a, lat_b, lon_b)
            if spatial_distance <= self.max_radius:
                spatial_score = max(0.0, 1.0 - (spatial_distance / self.max_radius))
            else:
                spatial_score = 0.0

        # 3. Temporal Proximity
        temporal_delta: Optional[float] = None
        temporal_score = 0.0
        if time_a and time_b:
            temporal_delta = abs((time_a - time_b).total_seconds())
            if temporal_delta <= self.max_time_seconds:
                temporal_score = max(0.0, 1.0 - (temporal_delta / self.max_time_seconds))
            else:
                temporal_score = 0.0

        # 4. Semantic Text Similarity (Active default: sparse_tfidf_ngram_v1)
        full_text_a = f"{title_a} {desc_a or ''} {loc_name_a or ''} {cat_a}".strip()
        full_text_b = f"{title_b} {desc_b or ''} {loc_name_b or ''} {cat_b}".strip()
        semantic_score = semantic_vectorizer.cosine_similarity(
            full_text_a, full_text_b, vec_a=vec_a, vec_b=vec_b
        )

        # 5. Location Entity Match
        res_a = location_resolver.resolve(
            text=full_text_a, latitude=lat_a, longitude=lon_a, location_name=loc_name_a
        )
        res_b = location_resolver.resolve(
            text=full_text_b, latitude=lat_b, longitude=lon_b, location_name=loc_name_b
        )
        entity_score = 0.5
        if res_a.city and res_b.city:
            if res_a.city.lower() == res_b.city.lower():
                if (
                    res_a.locality
                    and res_b.locality
                    and res_a.locality.lower() == res_b.locality.lower()
                ):
                    entity_score = 1.0
                else:
                    entity_score = 0.8
            else:
                entity_score = 0.0

        signals = DuplicateSignalBreakdown(
            spatial_distance_meters=round(spatial_distance, 1)
            if spatial_distance is not None
            else None,
            spatial_score=round(spatial_score, 4),
            temporal_delta_seconds=round(temporal_delta, 1) if temporal_delta is not None else None,
            temporal_score=round(temporal_score, 4),
            category_compatibility_score=round(cat_score, 4),
            semantic_similarity=round(semantic_score, 4),
            entity_compatibility_score=round(entity_score, 4),
            source_relationship_score=0.5,
        )

        # =========================================================================
        # 6. DECISION POLICY
        # =========================================================================
        # Hard Gate 1: Mutually exclusive hazard category
        if cat_score == 0.0:
            return DuplicateAssessment(
                candidate_report_id=report_a_id,
                reference_report_id=report_b_id,
                decision=DuplicateDecision.DISTINCT,
                overall_score=0.0,
                signals=signals,
                explanation=f"Incompatible hazard categories ({cat_a} vs {cat_b})",
                model_version=self.engine_version,
                semantic_method=self.semantic_method,
                assessed_at=datetime.now(timezone.utc),
            )

        # Hard Gate 2: Spatial distance exceeded
        if spatial_distance is not None and spatial_distance > self.max_radius:
            return DuplicateAssessment(
                candidate_report_id=report_a_id,
                reference_report_id=report_b_id,
                decision=DuplicateDecision.DISTINCT,
                overall_score=0.0,
                signals=signals,
                explanation=(
                    f"Distance ({spatial_distance:.0f}m) exceeds threshold ({self.max_radius:.0f}m)"
                ),
                model_version=self.engine_version,
                semantic_method=self.semantic_method,
                assessed_at=datetime.now(timezone.utc),
            )

        # Hard Gate 3: Temporal delta exceeded
        if temporal_delta is not None and temporal_delta > self.max_time_seconds:
            hours = temporal_delta / 3600.0
            max_h = self.max_time_seconds / 3600.0
            return DuplicateAssessment(
                candidate_report_id=report_a_id,
                reference_report_id=report_b_id,
                decision=DuplicateDecision.DISTINCT,
                overall_score=0.0,
                signals=signals,
                explanation=f"Time delta ({hours:.1f}h) exceeds max window ({max_h:.0f}h)",
                model_version=self.engine_version,
                semantic_method=self.semantic_method,
                assessed_at=datetime.now(timezone.utc),
            )

        # Gate 4: Entity Disjoint (Different cities confirmed)
        if entity_score == 0.0:
            return DuplicateAssessment(
                candidate_report_id=report_a_id,
                reference_report_id=report_b_id,
                decision=DuplicateDecision.DISTINCT,
                overall_score=0.0,
                signals=signals,
                explanation=f"Entities in different cities ({res_a.city} vs {res_b.city})",
                model_version=self.engine_version,
                semantic_method=self.semantic_method,
                assessed_at=datetime.now(timezone.utc),
            )

        # Compute multi-dimensional score
        if spatial_distance is not None and temporal_delta is not None:
            overall = (
                0.35 * spatial_score
                + 0.25 * temporal_score
                + 0.25 * semantic_score
                + 0.15 * cat_score
            )
            if overall >= self.confirmed_threshold and semantic_score >= 0.40:
                decision = DuplicateDecision.DUPLICATE
                explanation = (
                    f"Confirmed duplicate: distance={spatial_distance:.0f}m, "
                    f"time_delta={temporal_delta / 60:.0f}m, semantic_sim={semantic_score:.2f}"
                )
            elif overall >= self.possible_threshold:
                decision = DuplicateDecision.POSSIBLE_MATCH
                explanation = (
                    f"Probable match requiring verification: overall_score={overall:.2f}, "
                    f"semantic_sim={semantic_score:.2f}"
                )
            else:
                decision = DuplicateDecision.DISTINCT
                explanation = f"Distinct incident: overall similarity {overall:.2f} below threshold"
        else:
            # Incomplete spatial or temporal context
            overall = 0.60 * semantic_score + 0.40 * cat_score
            if semantic_score >= self.semantic_threshold and cat_score >= 0.70:
                decision = DuplicateDecision.POSSIBLE_MATCH
                explanation = (
                    f"Probable match on text/hazard (sim={semantic_score:.2f}) "
                    "but spatial or temporal coordinates are incomplete"
                )
            else:
                decision = DuplicateDecision.DISTINCT
                explanation = (
                    "Distinct incident: insufficient spatial/temporal evidence to confirm duplicate"
                )

        return DuplicateAssessment(
            candidate_report_id=report_a_id,
            reference_report_id=report_b_id,
            decision=decision,
            overall_score=round(overall, 4),
            signals=signals,
            explanation=explanation,
            model_version=self.engine_version,
            semantic_method=self.semantic_method,
            assessed_at=datetime.now(timezone.utc),
        )


duplicate_scorer = DuplicateScorer()
