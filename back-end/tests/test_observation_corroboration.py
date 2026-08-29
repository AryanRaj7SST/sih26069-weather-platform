"""Tests for Observation Corroboration Engine.

Covers:
- Scorer unit tests (7 signals, hard gates, context guard)
- Metric relevance & hazard policy (direct vs indirect)
- River entity substring safety ("Krishna Nagar" not river)
- Same basin different river context
- Contradictory conservative authoritative logic
- Incident time = None safe path
- Candidate generation completeness & anti-starvation
- Real PostGIS DWithin and distance in meters
- PostGIS failure remains a processing failure
- Grouping by (source_id, station_code)
- Water level validation without universal elevation limits
- Steady trend neutral semantics
- Human notes, score, and relationship decision protection
- updated_at semantics on re-evaluation
- 40-case synthetic benchmark evaluation
- DB integration (persistence, idempotency, human override)
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_GeogFromWKB
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import func, pool, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.intelligence.observation_candidate_generator import (
    ObservationCandidateGenerator,
)
from app.intelligence.observation_corroboration_engine import (
    ObservationCorroborationEngine,
)
from app.intelligence.observation_evaluation_dataset import (
    run_observation_benchmark,
)
from app.intelligence.observation_scorer import (
    ObservationScorer,
    WaterLevelPolicy,
    _is_river_entity_mention,
)
from app.intelligence.schemas import (
    ObservationDataQuality,
    ObservationRelationship,
    TrendAnalysisResult,
    TrendDirection,
)
from app.models.category import EventCategory
from app.models.corroboration import IncidentObservationCorroboration
from app.models.observation import WeatherObservation
from app.models.report import WeatherReport
from app.models.source import Source

# ═══════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════


@pytest_asyncio.fixture
async def db_session():
    """Create an isolated async database session per test with NullPool."""
    test_engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session

    await test_engine.dispose()


def _make_scorer(policy: Optional[WaterLevelPolicy] = None) -> ObservationScorer:
    """Create a scorer with default or custom policy."""
    return ObservationScorer(policy=policy or WaterLevelPolicy())


def _make_trend(
    direction: str = "RISING",
    delta: Optional[float] = 0.82,
    rate: Optional[float] = 0.27,
    points: int = 4,
    span: Optional[float] = 186.0,
    has_gaps: bool = False,
) -> TrendAnalysisResult:
    """Helper to create trend analysis results."""
    return TrendAnalysisResult(
        direction=TrendDirection(direction),
        delta_value=delta,
        rate_per_hour=rate,
        points_count=points,
        span_minutes=span,
        has_data_gaps=has_gaps,
        metric_key="water_level_m",
        station_code="CWC-TEST-STATION",
    )


_REF_TIME = datetime(2026, 8, 29, 10, 0, 0, tzinfo=timezone.utc)

_KRISHNA_METRICS: Dict[str, Any] = {
    "river": "Krishna",
    "basin": "Krishna",
    "tributary": None,
    "local_river": None,
    "state": "Karnataka",
    "district": "Yadgir",
}

_CAUVERY_METRICS: Dict[str, Any] = {
    "river": "Cauvery",
    "basin": "Cauvery",
    "tributary": None,
    "local_river": None,
    "state": "Karnataka",
    "district": "Mandya",
}


# ═══════════════════════════════════════════════════════════
# 1. Spatial Score Tests
# ═══════════════════════════════════════════════════════════


def test_spatial_score_at_zero():
    scorer = _make_scorer()
    assert scorer.compute_spatial_score(0.0) == 1.0


def test_spatial_score_at_radius():
    scorer = _make_scorer()
    assert scorer.compute_spatial_score(35000.0) == 0.0


def test_spatial_score_beyond_radius():
    scorer = _make_scorer()
    assert scorer.compute_spatial_score(40000.0) == 0.0


def test_spatial_score_midpoint():
    scorer = _make_scorer()
    score = scorer.compute_spatial_score(17500.0)
    assert score is not None
    assert 0.49 <= score <= 0.51


def test_spatial_score_missing():
    """Missing distance → None, not 0.0."""
    scorer = _make_scorer()
    assert scorer.compute_spatial_score(None) is None


# ═══════════════════════════════════════════════════════════
# 2. Temporal Score Tests
# ═══════════════════════════════════════════════════════════


def test_temporal_score_concurrent():
    """Observation within ±30 min → 1.0."""
    scorer = _make_scorer()
    score = scorer.compute_temporal_score(_REF_TIME - timedelta(minutes=10), _REF_TIME)
    assert score == 1.0


def test_temporal_score_prior_full():
    """Observation 2h prior (within 4h full window) → 1.0."""
    scorer = _make_scorer()
    score = scorer.compute_temporal_score(_REF_TIME - timedelta(hours=2), _REF_TIME)
    assert score == 1.0


def test_temporal_score_prior_decay():
    """Observation 12h prior → decaying below 1.0."""
    scorer = _make_scorer()
    score = scorer.compute_temporal_score(_REF_TIME - timedelta(hours=12), _REF_TIME)
    assert score is not None
    assert 0.0 < score < 1.0


def test_temporal_score_beyond_window():
    """Observation 25h away → 0.0."""
    scorer = _make_scorer()
    score = scorer.compute_temporal_score(_REF_TIME - timedelta(hours=25), _REF_TIME)
    assert score == 0.0


def test_temporal_score_post_decay():
    """Post-observation decays."""
    scorer = _make_scorer()
    score = scorer.compute_temporal_score(_REF_TIME + timedelta(hours=6), _REF_TIME)
    assert score is not None
    assert 0.0 < score < 1.0


def test_temporal_score_missing():
    """Missing timestamp → None."""
    scorer = _make_scorer()
    assert scorer.compute_temporal_score(None, _REF_TIME) is None
    assert scorer.compute_temporal_score(_REF_TIME, None) is None


# ═══════════════════════════════════════════════════════════
# 3. Metric Relevance & Hazard Policy Tests (USER-MANDATED)
# ═══════════════════════════════════════════════════════════


def test_metric_relevance_direct_hazards():
    scorer = _make_scorer()
    assert scorer.compute_metric_relevance("FLOOD_WATERLOGGING") == 1.0
    assert scorer.compute_metric_relevance("URBAN_FLOOD") == 1.0


def test_metric_relevance_indirect_hazards():
    scorer = _make_scorer()
    assert scorer.compute_metric_relevance("HEAVY_RAINFALL") == 0.55
    assert scorer.compute_metric_relevance("CYCLONE") == 0.55


def test_metric_relevance_incompatible():
    scorer = _make_scorer()
    assert scorer.compute_metric_relevance("HEATWAVE") == 0.0
    assert scorer.compute_metric_relevance("DROUGHT") == 0.0
    assert scorer.compute_metric_relevance("COLDWAVE") == 0.0
    assert scorer.compute_metric_relevance("LIGHTNING") == 0.0


def test_water_level_heavy_rainfall_cannot_strongly_corroborate():
    """Heavy rainfall + rising river level cannot reach CORROBORATING."""
    scorer = _make_scorer()
    assessment = scorer.score_corroboration(
        incident_id=uuid.uuid4(),
        observation_id=uuid.uuid4(),
        incident_category="HEAVY_RAINFALL",
        incident_lat=16.77,
        incident_lon=77.14,
        incident_time=_REF_TIME,
        incident_location_name="Flooding along Krishna River near Yadgir",
        incident_title="Heavy rainfall warning",
        incident_description="Monsoon rainfall",
        observation_water_level_m=525.0,
        observation_time=_REF_TIME - timedelta(minutes=15),
        observation_raw_metrics=_KRISHNA_METRICS,
        distance_meters=500.0,
        trend=_make_trend("RISING", delta=2.5, rate=0.8, points=6, span=180.0),
    )
    assert assessment.relationship_type != ObservationRelationship.CORROBORATING
    assert assessment.relationship_type == ObservationRelationship.CONSISTENT
    assert assessment.overall_score < scorer.policy.corroborating_threshold


def test_water_level_cyclone_cannot_strongly_corroborate():
    """Cyclone + rising river level cannot reach CORROBORATING."""
    scorer = _make_scorer()
    assessment = scorer.score_corroboration(
        incident_id=uuid.uuid4(),
        observation_id=uuid.uuid4(),
        incident_category="CYCLONE",
        incident_lat=16.77,
        incident_lon=77.14,
        incident_time=_REF_TIME,
        incident_location_name="Cyclone impact on Krishna River",
        incident_title="Cyclone warning",
        incident_description="Cyclone aftermath",
        observation_water_level_m=525.0,
        observation_time=_REF_TIME - timedelta(minutes=15),
        observation_raw_metrics=_KRISHNA_METRICS,
        distance_meters=500.0,
        trend=_make_trend("RISING", delta=2.5, rate=0.8, points=6, span=180.0),
    )
    assert assessment.relationship_type != ObservationRelationship.CORROBORATING
    assert assessment.relationship_type == ObservationRelationship.CONSISTENT


def test_water_level_flood_waterlogging_strong_path():
    """Flood waterlogging + same river + rising level CAN reach CORROBORATING."""
    scorer = _make_scorer()
    assessment = scorer.score_corroboration(
        incident_id=uuid.uuid4(),
        observation_id=uuid.uuid4(),
        incident_category="FLOOD_WATERLOGGING",
        incident_lat=16.77,
        incident_lon=77.14,
        incident_time=_REF_TIME,
        incident_location_name="Severe Krishna River flooding near Yadgir",
        incident_title="Flood emergency",
        incident_description="Krishna river overflowing",
        observation_water_level_m=525.0,
        observation_time=_REF_TIME - timedelta(minutes=15),
        observation_raw_metrics=_KRISHNA_METRICS,
        distance_meters=1000.0,
        trend=_make_trend("RISING", delta=1.5, rate=0.5, points=6, span=180.0),
    )
    assert assessment.relationship_type == ObservationRelationship.CORROBORATING
    assert assessment.overall_score >= scorer.policy.corroborating_threshold


# ═══════════════════════════════════════════════════════════
# 4. Context Guard & Text Matching Safety Tests (USER-MANDATED)
# ═══════════════════════════════════════════════════════════


def test_context_guard_raw_substring_krishna_nagar_not_river():
    """'Krishna Nagar' must NOT be treated as a river match for Krishna River station."""
    scorer = _make_scorer()
    score = scorer.compute_station_context_score(
        observation_raw_metrics=_KRISHNA_METRICS,
        incident_location_name="Waterlogging in Krishna Nagar, Delhi",
        incident_title="Delhi rain waterlogging",
        incident_description="Streets submerged in Krishna Nagar colony",
    )
    # Must NOT get 1.0 (river match). Suffix guard stops it.
    assert score <= 0.20
    assert not _is_river_entity_mention("Krishna Nagar", "Krishna")
    assert not _is_river_entity_mention("Krishna Colony", "Krishna")
    assert not _is_river_entity_mention("Krishna Layout", "Krishna")
    assert not _is_river_entity_mention("Krishna Marg", "Krishna")
    assert not _is_river_entity_mention("Krishna Road", "Krishna")
    assert _is_river_entity_mention("Krishna River", "Krishna")
    assert _is_river_entity_mention("River Krishna", "Krishna")
    assert _is_river_entity_mention("along the Krishna", "Krishna")
    assert _is_river_entity_mention("banks of Krishna", "Krishna")


def test_context_guard_river_in_location_name_strong():
    """River mentioned in location_name → STRONG station context."""
    scorer = _make_scorer()
    score = scorer.compute_station_context_score(
        observation_raw_metrics=_KRISHNA_METRICS,
        incident_location_name="Flooding along Krishna River near Yadgir",
        incident_title="Flood in Yadgir",
        incident_description="Heavy rain causing floods",
    )
    assert score == 1.0


def test_context_guard_same_basin_different_river_is_weak():
    """Same basin but explicitly different river → weak (0.15–0.20), never strong."""
    scorer = _make_scorer()
    metrics_with_different_river = {
        **_KRISHNA_METRICS,
        "river": "Tungabhadra",  # Different river, same basin
    }
    score = scorer.compute_station_context_score(
        observation_raw_metrics=metrics_with_different_river,
        incident_location_name="Krishna River flooding near Yadgir",
        incident_title="Krishna flood",
        incident_description="River overflowing",
    )
    # Incident specifies Krishna River, station is on Tungabhadra River
    assert score <= 0.20


def test_context_guard_river_only_in_description_weak():
    """River mentioned ONLY in description → WEAK context (not strong)."""
    scorer = _make_scorer()
    score = scorer.compute_station_context_score(
        observation_raw_metrics=_KRISHNA_METRICS,
        incident_location_name="Waterlogging at Andheri station, Mumbai",
        incident_title="Mumbai flooded after heavy rain",
        incident_description="Krishna river levels are rising while Mumbai receives heavy rain",
    )
    assert score <= 0.25


def test_context_guard_river_in_title_weak():
    """River mentioned in title but not location_name → weak (0.35–0.45)."""
    scorer = _make_scorer()
    score = scorer.compute_station_context_score(
        observation_raw_metrics=_KRISHNA_METRICS,
        incident_location_name="Suburban residential ward flooding",
        incident_title="Krishna river water entering town",
        incident_description="Houses submerged",
    )
    assert 0.35 <= score <= 0.45


def test_context_guard_state_only_no_strong():
    """State-only match → weak (0.20)."""
    scorer = _make_scorer()
    score = scorer.compute_station_context_score(
        observation_raw_metrics=_KRISHNA_METRICS,
        incident_location_name="Flooding in Karnataka",
        incident_title="Karnataka floods",
        incident_description="Heavy rain across state",
    )
    assert score <= 0.20


# ═══════════════════════════════════════════════════════════
# 5. Water Level Validation Tests (USER-MANDATED)
# ═══════════════════════════════════════════════════════════


def test_data_quality_valid():
    scorer = _make_scorer()
    quality, score = scorer.assess_data_quality(520.0, _REF_TIME, _REF_TIME)
    assert quality == ObservationDataQuality.VALID
    assert score == 1.0


def test_data_quality_high_elevation_gauge_valid():
    """Legitimate high-elevation gauges (e.g. 3200m in Himalayas) must NOT be rejected."""
    scorer = _make_scorer()
    quality, score = scorer.assess_data_quality(3200.5, _REF_TIME, _REF_TIME)
    assert quality == ObservationDataQuality.VALID
    assert score == 1.0


def test_data_quality_missing_metric():
    scorer = _make_scorer()
    quality, score = scorer.assess_data_quality(None, _REF_TIME, _REF_TIME)
    assert quality == ObservationDataQuality.MISSING_METRIC
    assert score == 0.0


def test_data_quality_nan_is_malformed():
    scorer = _make_scorer()
    quality, score = scorer.assess_data_quality(float("nan"), _REF_TIME, _REF_TIME)
    assert quality == ObservationDataQuality.MALFORMED
    assert score == 0.0


def test_data_quality_inf_is_malformed():
    scorer = _make_scorer()
    quality, score = scorer.assess_data_quality(float("inf"), _REF_TIME, _REF_TIME)
    assert quality == ObservationDataQuality.MALFORMED
    assert score == 0.0


def test_data_quality_stale():
    scorer = _make_scorer()
    quality, score = scorer.assess_data_quality(520.0, _REF_TIME - timedelta(hours=50), _REF_TIME)
    assert quality == ObservationDataQuality.STALE
    assert score == 0.1


# ═══════════════════════════════════════════════════════════
# 6. Steady Trend Semantics Tests (USER-MANDATED)
# ═══════════════════════════════════════════════════════════


def test_steady_trend_score_is_neutral():
    """Steady trend produces 0.40 score and cannot independently drive CORROBORATING."""
    scorer = _make_scorer()
    trend = _make_trend("STEADY", delta=0.01, rate=0.003, points=5, span=300.0)
    analyzer_score = scorer.score_corroboration(
        incident_id=uuid.uuid4(),
        observation_id=uuid.uuid4(),
        incident_category="FLOOD_WATERLOGGING",
        incident_lat=16.77,
        incident_lon=77.14,
        incident_time=_REF_TIME,
        incident_location_name="Flooding in Yadgir Krishna River area",
        incident_title="Flooding",
        incident_description="Water accumulation",
        observation_water_level_m=520.0,
        observation_time=_REF_TIME - timedelta(minutes=15),
        observation_raw_metrics=_KRISHNA_METRICS,
        distance_meters=1000.0,
        trend=trend,
    )
    # Capped at CONSISTENT (<= 0.60)
    assert analyzer_score.relationship_type == ObservationRelationship.CONSISTENT
    assert analyzer_score.overall_score <= 0.60


# ═══════════════════════════════════════════════════════════
# 7. Contradictory Conservative Logic Tests (USER-MANDATED)
# ═══════════════════════════════════════════════════════════


def test_stable_gauge_does_not_contradict_generic_street_flooding():
    """Stable river level must NOT contradict generic urban street waterlogging."""
    scorer = _make_scorer()
    assessment = scorer.score_corroboration(
        incident_id=uuid.uuid4(),
        observation_id=uuid.uuid4(),
        incident_category="FLOOD_WATERLOGGING",
        incident_lat=16.77,
        incident_lon=77.14,
        incident_time=_REF_TIME,
        incident_location_name="Water accumulation on Yadgir Main Road",
        incident_title="Severe waterlogging on city streets",
        incident_description="Drainage overflow causing street flooding",
        observation_water_level_m=518.0,
        observation_time=_REF_TIME - timedelta(minutes=30),
        observation_raw_metrics=_KRISHNA_METRICS,
        distance_meters=1500.0,
        trend=_make_trend("STEADY", delta=0.01, rate=0.003, points=5, span=300.0),
    )
    assert assessment.relationship_type != ObservationRelationship.CONTRADICTORY


def test_contradictory_requires_authoritative_threshold():
    """Contradictory requires explicit danger_level threshold & observed level far below it."""
    scorer = _make_scorer()
    metrics_with_danger = {
        **_KRISHNA_METRICS,
        "danger_level": 530.0,
        "warning_level": 525.0,
    }
    assessment = scorer.score_corroboration(
        incident_id=uuid.uuid4(),
        observation_id=uuid.uuid4(),
        incident_category="FLOOD_WATERLOGGING",
        incident_lat=16.77,
        incident_lon=77.14,
        incident_time=_REF_TIME,
        incident_location_name="Severe Krishna River flooding Yadgir",
        incident_title="Major flood emergency - danger level breached",
        incident_description="River overflowing banks, catastrophic flooding",
        observation_water_level_m=515.0,  # 15m below danger level
        observation_time=_REF_TIME - timedelta(minutes=30),
        observation_raw_metrics=metrics_with_danger,
        distance_meters=1500.0,
        trend=_make_trend("STEADY", delta=0.01, rate=0.003, points=5, span=300.0),
    )
    assert assessment.relationship_type == ObservationRelationship.CONTRADICTORY


def test_not_contradictory_without_authoritative_threshold():
    """Without authoritative danger_level in metrics, alarming wording alone does NOT contradict."""
    scorer = _make_scorer()
    # Same scenario but NO danger_level in telemetry metrics
    assessment = scorer.score_corroboration(
        incident_id=uuid.uuid4(),
        observation_id=uuid.uuid4(),
        incident_category="FLOOD_WATERLOGGING",
        incident_lat=16.77,
        incident_lon=77.14,
        incident_time=_REF_TIME,
        incident_location_name="Severe Krishna River flooding Yadgir",
        incident_title="Major flood emergency",
        incident_description="River overflowing banks, evacuation ordered",
        observation_water_level_m=515.0,
        observation_time=_REF_TIME - timedelta(minutes=30),
        observation_raw_metrics=_KRISHNA_METRICS,  # No danger_level key
        distance_meters=1500.0,
        trend=_make_trend("STEADY", delta=0.01, rate=0.003, points=5, span=300.0),
    )
    # Must NOT be CONTRADICTORY without authoritative telemetry baseline
    assert assessment.relationship_type != ObservationRelationship.CONTRADICTORY


# ═══════════════════════════════════════════════════════════
# 8. PostGIS Failure vs Missing Coordinates (USER-MANDATED)
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_missing_coordinates_safely_returns_none_distance(
    db_session: AsyncSession,
):
    """Missing incident/observation coordinates safely return None without DB execution."""
    engine = ObservationCorroborationEngine()

    obs = WeatherObservation(
        station_code="CWC-NO-GEOM",
        station_name="No Geom Station",
        geom=None,  # No geometry
    )

    # Missing incident coordinates
    dist1 = await engine._compute_distance(
        db=db_session,
        observation=obs,
        incident_lat=None,
        incident_lon=None,
    )
    assert dist1 is None

    # Missing observation coordinates
    dist2 = await engine._compute_distance(
        db=db_session,
        observation=obs,
        incident_lat=16.77,
        incident_lon=77.14,
    )
    assert dist2 is None


@pytest.mark.asyncio
async def test_postgis_failure_raises_processing_failure(
    db_session: AsyncSession,
):
    """PostGIS/database execution error must RAISE an exception, NOT silently return None."""
    engine = ObservationCorroborationEngine()

    obs = WeatherObservation(
        id=uuid.uuid4(),
        station_code="CWC-ERROR-STATION",
        station_name="Error Station",
        geom=from_shape(Point(77.14, 16.77), srid=4326),
    )

    # Mock db.execute to raise a database exception
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.side_effect = Exception("PostGIS calculation failed")

    with pytest.raises(Exception, match="PostGIS calculation failed"):
        await engine._compute_distance(
            db=mock_session,
            observation=obs,
            incident_lat=16.77,
            incident_lon=77.14,
        )


# ═══════════════════════════════════════════════════════════
# 9. Real PostGIS PostgreSQL Tests (USER-MANDATED)
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_real_postgis_dwithin_works(db_session: AsyncSession):
    """Verify PostGIS ST_DWithin and spatial filtering on real PostgreSQL."""
    p1 = func.ST_SetSRID(func.ST_MakePoint(77.14, 16.77), 4326)
    p2 = func.ST_SetSRID(func.ST_MakePoint(77.15, 16.78), 4326)
    p3 = func.ST_SetSRID(func.ST_MakePoint(77.50, 17.20), 4326)

    # DWithin 35km for nearby point (1.5km) -> True
    stmt_near = select(ST_DWithin(ST_GeogFromWKB(p1), ST_GeogFromWKB(p2), 35000.0))
    is_near_within = (await db_session.execute(stmt_near)).scalar()
    assert is_near_within is True

    # DWithin 35km for distant point (~50km) -> False
    stmt_far = select(ST_DWithin(ST_GeogFromWKB(p1), ST_GeogFromWKB(p3), 35000.0))
    is_far_within = (await db_session.execute(stmt_far)).scalar()
    assert is_far_within is False


@pytest.mark.asyncio
async def test_real_postgis_distance_returns_meters(db_session: AsyncSession):
    """Verify PostGIS ST_Distance on geography returns distances in meters."""
    p1 = func.ST_SetSRID(func.ST_MakePoint(77.14, 16.77), 4326)
    p2 = func.ST_SetSRID(func.ST_MakePoint(77.15, 16.78), 4326)

    stmt = select(ST_Distance(ST_GeogFromWKB(p1), ST_GeogFromWKB(p2)))
    distance = (await db_session.execute(stmt)).scalar()

    assert distance is not None
    # 0.01 deg delta is ~1.5 km (1536 meters)
    assert 1400.0 <= distance <= 1700.0


# ═══════════════════════════════════════════════════════════
# 10. Candidate Generation & Multi-Source Grouping Tests (USER-MANDATED)
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_candidate_cap_does_not_starve_stations(db_session: AsyncSession):
    """A station with 20 readings must NOT starve another station with 1 reading."""
    gen = ObservationCandidateGenerator()

    source_stmt = select(Source).where(Source.source_code == "CWC_NWDP")
    source = (await db_session.execute(source_stmt)).scalar_one_or_none()
    if not source:
        source = Source(
            source_code="CWC_NWDP",
            name="CWC Test",
            source_type="GOV_OPEN_DATA",
            base_trust_score=0.92,
        )
        db_session.add(source)
        await db_session.flush()

    # Create 10 observations at Station A
    station_a_obs = []
    for i in range(10):
        obs = WeatherObservation(
            source_id=source.id,
            station_code="CWC-STATION-A-BURST",
            station_name="Station A",
            geom=from_shape(Point(77.14, 16.77), srid=4326),
            observed_at=_REF_TIME - timedelta(minutes=i * 5),
            water_level_m=520.0 + i * 0.1,
            raw_metrics=_KRISHNA_METRICS,
        )
        db_session.add(obs)
        station_a_obs.append(obs)

    # Create 1 observation at Station B (older by 2h)
    obs_b = WeatherObservation(
        source_id=source.id,
        station_code="CWC-STATION-B-SINGLE",
        station_name="Station B",
        geom=from_shape(Point(77.145, 16.775), srid=4326),
        observed_at=_REF_TIME - timedelta(hours=2),
        water_level_m=518.0,
        raw_metrics=_KRISHNA_METRICS,
    )
    db_session.add(obs_b)
    await db_session.flush()

    # Query with limit=5 (smaller than Station A's 10 readings)
    candidates, is_truncated = await gen.get_candidates(
        db=db_session,
        incident_lat=16.77,
        incident_lon=77.14,
        incident_time=_REF_TIME,
        spatial_radius_meters=35000.0,
        time_window_hours=24.0,
        candidate_limit=5,
    )

    station_codes = [c.station_code for c in candidates]
    # Both Station A and Station B must be present
    assert "CWC-STATION-A-BURST" in station_codes
    assert "CWC-STATION-B-SINGLE" in station_codes

    # Cleanup
    for o in station_a_obs:
        await db_session.delete(o)
    await db_session.delete(obs_b)
    await db_session.commit()


@pytest.mark.asyncio
async def test_grouping_by_source_id_and_station_code(db_session: AsyncSession):
    """Same station_code from two different sources must produce two distinct candidates."""
    gen = ObservationCandidateGenerator()

    # Source 1
    s1 = Source(
        source_code=f"SRC1_{uuid.uuid4().hex[:6]}",
        name="Source 1",
        source_type="GOV_OPEN_DATA",
        base_trust_score=0.90,
    )
    # Source 2
    s2 = Source(
        source_code=f"SRC2_{uuid.uuid4().hex[:6]}",
        name="Source 2",
        source_type="GOV_OPEN_DATA",
        base_trust_score=0.85,
    )
    db_session.add_all([s1, s2])
    await db_session.flush()

    # Same station code "ST-COMMON-99" across both sources
    obs1 = WeatherObservation(
        source_id=s1.id,
        station_code="ST-COMMON-99",
        station_name="Common Station",
        geom=from_shape(Point(77.14, 16.77), srid=4326),
        observed_at=_REF_TIME,
        water_level_m=520.0,
        raw_metrics=_KRISHNA_METRICS,
    )
    obs2 = WeatherObservation(
        source_id=s2.id,
        station_code="ST-COMMON-99",
        station_name="Common Station",
        geom=from_shape(Point(77.14, 16.77), srid=4326),
        observed_at=_REF_TIME,
        water_level_m=521.0,
        raw_metrics=_KRISHNA_METRICS,
    )
    db_session.add_all([obs1, obs2])
    await db_session.flush()

    candidates, _ = await gen.get_candidates(
        db=db_session,
        incident_lat=16.77,
        incident_lon=77.14,
        incident_time=_REF_TIME,
        spatial_radius_meters=35000.0,
        time_window_hours=24.0,
        candidate_limit=10,
    )

    common_candidates = [c for c in candidates if c.station_code == "ST-COMMON-99"]
    # Must contain both sources, not collapsed into 1
    assert len(common_candidates) == 2
    source_ids = {c.source_id for c in common_candidates}
    assert s1.id in source_ids
    assert s2.id in source_ids

    # Cleanup
    await db_session.delete(obs1)
    await db_session.delete(obs2)
    await db_session.delete(s1)
    await db_session.delete(s2)
    await db_session.commit()


# ═══════════════════════════════════════════════════════════
# 11. Incident Time = None Safe Path Test (USER-MANDATED)
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_incident_time_none_safe_path(db_session: AsyncSession):
    """Evaluating an incident with occurred_at = None must complete safely."""
    engine = ObservationCorroborationEngine()

    source_stmt = select(Source).where(Source.source_code == "CWC_NWDP")
    source = (await db_session.execute(source_stmt)).scalar_one_or_none()
    if not source:
        source = Source(
            source_code="CWC_NWDP",
            name="CWC Test",
            source_type="GOV_OPEN_DATA",
            base_trust_score=0.92,
        )
        db_session.add(source)
        await db_session.flush()

    cat_stmt = select(EventCategory).where(EventCategory.category_code == "FLOOD_WATERLOGGING")
    category = (await db_session.execute(cat_stmt)).scalar_one_or_none()

    # Incident inserted with valid timestamp, then occurred_at set to None in Python
    incident = WeatherReport(
        tracking_id=f"CORR-NOTIME-{uuid.uuid4().hex[:8]}",
        source_id=source.id,
        category_id=category.id if category else None,
        title="Incident without occurrence time",
        description="Testing safety when time is missing",
        location_name="Krishna flooding Yadgir",
        geom=from_shape(Point(77.14, 16.77), srid=4326),
        latitude=16.77,
        longitude=77.14,
        occurred_at=_REF_TIME,
        severity="MODERATE",
    )
    db_session.add(incident)
    await db_session.flush()

    # Test trend analyzer directly with anchor_time = None
    trend_direct = await engine.trend_analyzer.analyze_water_level_trend(
        db=db_session,
        station_code="CWC-KRISHNA-NOTIME",
        source_id=None,
        anchor_time=None,
    )
    assert trend_direct.direction == TrendDirection.INSUFFICIENT_DATA
    assert trend_direct.points_count == 0

    # Test engine with occurred_at = None on a detached report object
    db_session.expunge(incident)
    setattr(incident, "occurred_at", None)

    observation = WeatherObservation(
        source_id=source.id,
        station_code="CWC-KRISHNA-NOTIME",
        station_name="Yadgir NoTime",
        geom=from_shape(Point(77.14, 16.77), srid=4326),
        observed_at=_REF_TIME,
        water_level_m=520.0,
        raw_metrics=_KRISHNA_METRICS,
    )
    db_session.add(observation)
    await db_session.flush()

    # Must complete safely without exception
    result = await engine.evaluate_single_pair(db_session, incident, observation)
    await db_session.commit()

    assert result.is_persisted is True
    assert result.assessment.signals.temporal_score is None
    assert result.assessment.signals.temporal_delta_seconds is None

    # Cleanup
    row_stmt = select(IncidentObservationCorroboration).where(
        IncidentObservationCorroboration.id == result.corroboration_id
    )
    row = (await db_session.execute(row_stmt)).scalar_one_or_none()
    if row:
        await db_session.delete(row)
    await db_session.delete(observation)
    inc_db = (
        await db_session.execute(select(WeatherReport).where(WeatherReport.id == incident.id))
    ).scalar_one_or_none()
    if inc_db:
        await db_session.delete(inc_db)
    await db_session.commit()


# ═══════════════════════════════════════════════════════════
# 12. 40-Case Benchmark Evaluation
# ═══════════════════════════════════════════════════════════


def test_observation_benchmark_40_cases():
    """Run all 40 benchmark cases and verify metrics."""
    scorer = _make_scorer()
    metrics = run_observation_benchmark(scorer)

    assert metrics["total_cases"] == 40
    assert metrics["accuracy"] >= 0.85
    assert metrics["precision"] >= 0.80
    assert metrics["recall"] >= 0.80
    assert metrics["f1"] >= 0.80


def test_observation_benchmark_no_false_contradictory():
    scorer = _make_scorer()
    metrics = run_observation_benchmark(scorer)

    false_contradictory = [
        c
        for c in metrics["cases"]
        if c["actual"] == "CONTRADICTORY" and c["expected"] != "CONTRADICTORY"
    ]
    assert len(false_contradictory) == 0


def test_observation_benchmark_no_false_corroborating_for_irrelevant():
    scorer = _make_scorer()
    metrics = run_observation_benchmark(scorer)

    false_corroborating = [
        c
        for c in metrics["cases"]
        if c["actual"] == "CORROBORATING" and c["expected"] in ("IRRELEVANT", "INSUFFICIENT_DATA")
    ]
    assert len(false_corroborating) == 0


# ═══════════════════════════════════════════════════════════
# 13. DB Integration & Human Override Protection Tests (USER-MANDATED)
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_persist_corroboration_creates_row(db_session: AsyncSession):
    """Persisting a corroboration creates exactly one row."""
    engine = ObservationCorroborationEngine()

    source_stmt = select(Source).where(Source.source_code == "CWC_NWDP")
    source = (await db_session.execute(source_stmt)).scalar_one_or_none()
    if not source:
        source = Source(
            source_code="CWC_NWDP",
            name="CWC Test",
            source_type="GOV_OPEN_DATA",
            base_trust_score=0.92,
        )
        db_session.add(source)
        await db_session.flush()

    cat_stmt = select(EventCategory).where(EventCategory.category_code == "FLOOD_WATERLOGGING")
    category = (await db_session.execute(cat_stmt)).scalar_one_or_none()

    incident = WeatherReport(
        tracking_id=f"CORR-TEST-{uuid.uuid4().hex[:8]}",
        source_id=source.id,
        category_id=category.id if category else None,
        title="Test flood incident for corroboration",
        description="Krishna River flooding near Yadgir for testing",
        location_name="Krishna River flooding Yadgir",
        geom=from_shape(Point(77.14, 16.77), srid=4326),
        latitude=16.77,
        longitude=77.14,
        occurred_at=_REF_TIME,
        severity="SEVERE",
    )
    db_session.add(incident)
    await db_session.flush()

    observation = WeatherObservation(
        source_id=source.id,
        station_code="CWC-KRISHNA-YADGIR",
        station_name="Yadgir",
        geom=from_shape(Point(77.14, 16.77), srid=4326),
        observed_at=_REF_TIME - timedelta(hours=1),
        water_level_m=520.5,
        raw_metrics=_KRISHNA_METRICS,
    )
    db_session.add(observation)
    await db_session.flush()

    result = await engine.evaluate_single_pair(db_session, incident, observation)
    await db_session.commit()

    assert result.is_persisted is True
    assert result.corroboration_id is not None

    row_stmt = select(IncidentObservationCorroboration).where(
        IncidentObservationCorroboration.id == result.corroboration_id
    )
    row = (await db_session.execute(row_stmt)).scalar_one_or_none()
    assert row is not None
    assert row.corroboration_assessment is not None
    assert row.corroboration_assessment.get("is_human_override") is False

    await db_session.delete(row)
    await db_session.delete(observation)
    await db_session.delete(incident)
    await db_session.commit()


@pytest.mark.asyncio
async def test_updated_at_semantics_on_reprocessing(db_session: AsyncSession):
    """Repeated automated updates refresh updated_at while preserving created_at."""
    engine = ObservationCorroborationEngine()

    source_stmt = select(Source).where(Source.source_code == "CWC_NWDP")
    source = (await db_session.execute(source_stmt)).scalar_one_or_none()
    if not source:
        source = Source(
            source_code="CWC_NWDP",
            name="CWC Test",
            source_type="GOV_OPEN_DATA",
            base_trust_score=0.92,
        )
        db_session.add(source)
        await db_session.flush()

    incident = WeatherReport(
        tracking_id=f"CORR-UPDT-{uuid.uuid4().hex[:8]}",
        source_id=source.id,
        title="Updated_at test incident",
        description="Testing timestamp updates",
        location_name="Krishna flooding Yadgir",
        geom=from_shape(Point(77.14, 16.77), srid=4326),
        latitude=16.77,
        longitude=77.14,
        occurred_at=_REF_TIME,
        severity="MODERATE",
    )
    db_session.add(incident)
    await db_session.flush()

    observation = WeatherObservation(
        source_id=source.id,
        station_code="CWC-KRISHNA-UPDT",
        station_name="Yadgir Updt",
        geom=from_shape(Point(77.14, 16.77), srid=4326),
        observed_at=_REF_TIME - timedelta(hours=1),
        water_level_m=520.0,
        raw_metrics=_KRISHNA_METRICS,
    )
    db_session.add(observation)
    await db_session.flush()

    # Pass 1
    res1 = await engine.evaluate_single_pair(db_session, incident, observation)
    await db_session.commit()

    row_stmt = select(IncidentObservationCorroboration).where(
        IncidentObservationCorroboration.id == res1.corroboration_id
    )
    row1 = (await db_session.execute(row_stmt)).scalar_one()
    created_at_1 = row1.created_at
    updated_at_1 = row1.updated_at

    # Pass 2: Re-evaluate
    await engine.evaluate_single_pair(db_session, incident, observation)
    await db_session.commit()

    row2 = (await db_session.execute(row_stmt)).scalar_one()
    assert row2.created_at == created_at_1
    assert row2.updated_at >= updated_at_1

    await db_session.delete(row2)
    await db_session.delete(observation)
    await db_session.delete(incident)
    await db_session.commit()


@pytest.mark.asyncio
async def test_human_notes_and_override_preserved(db_session: AsyncSession):
    """Human override and human notes MUST remain completely unchanged.

    Automated reprocessing must never overwrite operator decisions or notes.
    """
    engine = ObservationCorroborationEngine()

    source_stmt = select(Source).where(Source.source_code == "CWC_NWDP")
    source = (await db_session.execute(source_stmt)).scalar_one_or_none()
    if not source:
        source = Source(
            source_code="CWC_NWDP",
            name="CWC Test",
            source_type="GOV_OPEN_DATA",
            base_trust_score=0.92,
        )
        db_session.add(source)
        await db_session.flush()

    cat_stmt = select(EventCategory).where(EventCategory.category_code == "FLOOD_WATERLOGGING")
    category = (await db_session.execute(cat_stmt)).scalar_one_or_none()

    incident = WeatherReport(
        tracking_id=f"CORR-OVERRIDE-{uuid.uuid4().hex[:8]}",
        source_id=source.id,
        category_id=category.id if category else None,
        title="Human override test",
        description="Testing override preservation",
        location_name="Krishna flooding Yadgir",
        geom=from_shape(Point(77.14, 16.77), srid=4326),
        latitude=16.77,
        longitude=77.14,
        occurred_at=_REF_TIME,
        severity="SEVERE",
    )
    db_session.add(incident)
    await db_session.flush()

    observation = WeatherObservation(
        source_id=source.id,
        station_code="CWC-KRISHNA-OVERRIDE",
        station_name="Override Station",
        geom=from_shape(Point(77.14, 16.77), srid=4326),
        observed_at=_REF_TIME - timedelta(hours=1),
        water_level_m=520.0,
        raw_metrics=_KRISHNA_METRICS,
    )
    db_session.add(observation)
    await db_session.flush()

    result1 = await engine.evaluate_single_pair(db_session, incident, observation)
    await db_session.commit()

    row_stmt = select(IncidentObservationCorroboration).where(
        IncidentObservationCorroboration.id == result1.corroboration_id
    )
    row = (await db_session.execute(row_stmt)).scalar_one()

    # Operator sets human override
    human_assessment = row.corroboration_assessment or {}
    human_assessment["is_human_override"] = True
    human_assessment["relationship_type"] = "CORROBORATING"
    row.corroboration_assessment = human_assessment
    row.corroboration_score = 0.95
    row.corroboration_notes = "Operator verified: field team confirmed station gauge"
    created_at_orig = row.created_at
    await db_session.commit()

    # Automated reprocessing occurs
    result2 = await engine.evaluate_single_pair(db_session, incident, observation)
    await db_session.commit()
    assert result2.corroboration_id == result1.corroboration_id

    # Verify all 3 human attributes remain intact
    row2 = (await db_session.execute(row_stmt)).scalar_one()
    assert row2.corroboration_notes == "Operator verified: field team confirmed station gauge"
    assert row2.corroboration_score == 0.95
    assert row2.corroboration_assessment is not None
    assert row2.corroboration_assessment.get("is_human_override") is True
    assert row2.corroboration_assessment.get("relationship_type") == "CORROBORATING"
    assert "last_automated_assessment" in row2.corroboration_assessment
    assert row2.created_at == created_at_orig

    await db_session.delete(row2)
    await db_session.delete(observation)
    await db_session.delete(incident)
    await db_session.commit()
