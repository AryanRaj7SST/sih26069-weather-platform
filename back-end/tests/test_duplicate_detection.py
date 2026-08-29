import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import pool, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.intelligence import (
    CandidateGenerator,
    DuplicateDecision,
    DuplicateScorer,
    IncidentClusteringEngine,
    SemanticVectorizer,
    duplicate_scorer,
    evaluate_threshold_sensitivity,
    get_category_compatibility,
    run_benchmark_evaluation,
)
from app.models.category import EventCategory
from app.models.duplicate import DuplicateCluster
from app.models.report import WeatherReport
from app.models.source import Source


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


def test_category_compatibility_matrix():
    """Verify hazard category relationships and hard incompatibility gates."""
    # Identical categories
    assert get_category_compatibility("FLOOD_WATERLOGGING", "FLOOD_WATERLOGGING") == 1.0
    assert get_category_compatibility("HEAVY_RAINFALL", "heavy_rainfall") == 1.0

    # Related categories
    assert get_category_compatibility("FLOOD_WATERLOGGING", "HEAVY_RAINFALL") == 0.75
    assert get_category_compatibility("THUNDERSTORM", "LIGHTNING") == 0.85

    # Strictly incompatible hazards (hard gate: 0.0)
    assert get_category_compatibility("HEATWAVE", "FLOOD_WATERLOGGING") == 0.0
    assert get_category_compatibility("COLDWAVE", "HEATWAVE") == 0.0
    assert get_category_compatibility("DROUGHT", "HEAVY_RAINFALL") == 0.0


def test_semantic_vectorizer_similarity():
    """Verify deterministic TF-IDF term vectorizer and cosine similarity."""
    vectorizer = SemanticVectorizer()

    # Identical texts
    sim_identical = vectorizer.cosine_similarity(
        "Knee-deep water inside Andheri subway", "Knee-deep water inside Andheri subway"
    )
    assert sim_identical == 1.0

    # High semantic overlap
    sim_high = vectorizer.cosine_similarity(
        "Severe waterlogging near Andheri station entrance",
        "Knee deep water outside Andheri railway station subway",
    )
    assert sim_high >= 0.50

    # Completely disjoint texts
    sim_disjoint = vectorizer.cosine_similarity(
        "Extreme heat wave scorching desert fields",
        "Heavy snowfall in high mountain pass",
    )
    assert sim_disjoint < 0.20


def test_duplicate_scorer_hard_gates():
    """Verify hard rejection gates for category, distance, and time."""
    scorer = DuplicateScorer()
    rep_a = uuid.uuid4()
    rep_b = uuid.uuid4()

    # Gate 1: Mutually exclusive category -> DISTINCT
    res_cat = scorer.score_pair(
        report_a_id=rep_a,
        report_b_id=rep_b,
        title_a="Severe heatwave in Mumbai",
        title_b="Flash flood in Mumbai",
        desc_a="High heat",
        desc_b="Deep flood",
        cat_a="HEATWAVE",
        cat_b="FLOOD_WATERLOGGING",
        lat_a=19.0760,
        lon_a=72.8777,
        lat_b=19.0760,
        lon_b=72.8777,
        time_a=datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        time_b=datetime(2026, 8, 29, 10, 5, tzinfo=timezone.utc),
    )
    assert res_cat.decision == DuplicateDecision.DISTINCT
    assert "Incompatible" in res_cat.explanation

    # Gate 2: Distance > 2.5km -> DISTINCT
    res_dist = scorer.score_pair(
        report_a_id=rep_a,
        report_b_id=rep_b,
        title_a="Waterlogging in Andheri",
        title_b="Waterlogging in Thane",
        desc_a="Subway flooded",
        desc_b="Subway flooded",
        cat_a="FLOOD_WATERLOGGING",
        cat_b="FLOOD_WATERLOGGING",
        lat_a=19.1197,
        lon_a=72.8468,  # Andheri
        lat_b=19.2183,
        lon_b=72.9781,  # Thane (~17 km away)
        time_a=datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        time_b=datetime(2026, 8, 29, 10, 10, tzinfo=timezone.utc),
    )
    assert res_dist.decision == DuplicateDecision.DISTINCT
    assert "Distance" in res_dist.explanation

    # Gate 3: Time delta > 3 hours -> DISTINCT
    res_time = scorer.score_pair(
        report_a_id=rep_a,
        report_b_id=rep_b,
        title_a="Waterlogging in Andheri",
        title_b="Waterlogging in Andheri",
        desc_a="Subway flooded",
        desc_b="Subway flooded",
        cat_a="FLOOD_WATERLOGGING",
        cat_b="FLOOD_WATERLOGGING",
        lat_a=19.1197,
        lon_a=72.8468,
        lat_b=19.1197,
        lon_b=72.8468,
        time_a=datetime(2026, 8, 27, 10, 0, tzinfo=timezone.utc),
        time_b=datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),  # 48 hours later
    )
    assert res_time.decision == DuplicateDecision.DISTINCT
    assert "Time delta" in res_time.explanation


def test_duplicate_scorer_confirmed_and_possible():
    """Verify scoring logic for confirmed DUPLICATE vs POSSIBLE_MATCH."""
    scorer = DuplicateScorer()
    rep_a = uuid.uuid4()
    rep_b = uuid.uuid4()

    # Confirmed Duplicate: Same place, close time, same hazard, high semantic match
    res_dup = scorer.score_pair(
        report_a_id=rep_a,
        report_b_id=rep_b,
        title_a="Severe waterlogging near Andheri station",
        title_b="Knee-deep water outside Andheri station subway",
        desc_a="Water knee-deep near Andheri railway station subway entrance.",
        desc_b="Subway completely inundated, traffic halted near Andheri station.",
        cat_a="FLOOD_WATERLOGGING",
        cat_b="FLOOD_WATERLOGGING",
        lat_a=19.1197,
        lon_a=72.8468,
        lat_b=19.1202,
        lon_b=72.8472,  # 70 meters away
        time_a=datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        time_b=datetime(2026, 8, 29, 10, 15, tzinfo=timezone.utc),  # 15 mins delta
        loc_name_a="Andheri station, Mumbai",
        loc_name_b="Andheri, Mumbai",
    )
    assert res_dup.decision == DuplicateDecision.DUPLICATE
    assert res_dup.overall_score >= 0.75

    # Possible Match: Unresolved coordinates with high text similarity
    res_possible = scorer.score_pair(
        report_a_id=rep_a,
        report_b_id=rep_b,
        title_a="Bridge collapse feared as flood waters breach embankment",
        title_b="Bridge collapse feared as flood waters breach embankment",
        desc_a="Authorities evacuate residents near river.",
        desc_b="Authorities evacuate residents near river.",
        cat_a="FLOOD_WATERLOGGING",
        cat_b="FLOOD_WATERLOGGING",
        lat_a=None,
        lon_a=None,
        lat_b=None,
        lon_b=None,
        time_a=datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        time_b=datetime(2026, 8, 29, 10, 10, tzinfo=timezone.utc),
    )
    assert res_possible.decision == DuplicateDecision.POSSIBLE_MATCH
    assert "incomplete" in res_possible.explanation


def test_expanded_benchmark_evaluation_dataset():
    """Verify precision, recall, and zero false merges on expanded 30-pair benchmark."""
    metrics = run_benchmark_evaluation(duplicate_scorer)

    assert metrics["total_pairs"] == 30
    assert metrics["false_merges"] == 0  # CRITICAL: zero false merges
    assert metrics["false_positives"] == 0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0
    assert metrics["all_passed"] is True


def test_threshold_sensitivity_evaluation():
    """Verify threshold evaluation runs across candidate thresholds without errors."""
    sensitivity = evaluate_threshold_sensitivity([0.65, 0.70, 0.75, 0.80, 0.85])
    assert len(sensitivity) == 5

    # Confirm 0.75 confirmed threshold provides zero false merges
    t75 = next(s for s in sensitivity if s["confirmed_threshold"] == 0.75)
    assert t75["false_merges"] == 0
    assert t75["precision"] == 1.0


def test_deterministic_primary_selection():
    """Verify deterministic primary selection prioritizes earliest occurrence time."""
    t1 = datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 29, 10, 30, tzinfo=timezone.utc)

    rep_earlier = WeatherReport(
        id=uuid.uuid4(),
        tracking_id="TRK-EARLIER",
        occurred_at=t1,
        credibility_score=0.5,
    )
    rep_later = WeatherReport(
        id=uuid.uuid4(),
        tracking_id="TRK-LATER",
        occurred_at=t2,
        credibility_score=0.8,
    )

    primary = IncidentClusteringEngine.select_primary_report(rep_later, rep_earlier)
    assert primary.id == rep_earlier.id


@pytest.mark.asyncio
async def test_candidate_generation_truncation_detection(db_session: AsyncSession):
    """Verify CandidateGenerator exposes is_truncated when candidate count reaches query limit."""
    from unittest.mock import MagicMock

    candidate_gen = CandidateGenerator(default_limit=2)

    # Mock execute returning 3 items when limit is 2
    mock_rep1 = WeatherReport(id=uuid.uuid4(), occurred_at=datetime.now(timezone.utc))
    mock_rep2 = WeatherReport(id=uuid.uuid4(), occurred_at=datetime.now(timezone.utc))
    mock_rep3 = WeatherReport(id=uuid.uuid4(), occurred_at=datetime.now(timezone.utc))

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_rep1, mock_rep2, mock_rep3]
    mock_res = MagicMock()
    mock_res.scalars.return_value = mock_scalars

    with patch.object(db_session, "execute", new=AsyncMock(return_value=mock_res)):
        pt = Point(72.8468, 19.1197)
        res = await candidate_gen.get_candidates(
            db=db_session,
            report_id=uuid.uuid4(),
            geom=from_shape(pt, srid=4326),
            occurred_at=datetime.now(timezone.utc),
            limit=2,
        )

        assert len(res.candidates) == 2
        assert res.total_found == 3
        assert res.is_truncated is True


@pytest.mark.asyncio
async def test_incident_clustering_end_to_end_in_db(db_session: AsyncSession):
    """Verify duplicate clustering flow, human status separation, and persistence."""
    engine = IncidentClusteringEngine()

    # 1. Setup Source & Category
    src_stmt = select(Source).where(Source.source_code == "CITIZEN")
    src_res = await db_session.execute(src_stmt)
    source = src_res.scalar_one_or_none()
    if not source:
        source = Source(
            source_code="CITIZEN",
            name="Citizen Report Ingestion",
            source_type="CITIZEN",
            base_trust_score=0.5,
            is_active=True,
        )
        db_session.add(source)
        await db_session.flush()

    cat_stmt = select(EventCategory).where(EventCategory.category_code == "FLOOD_WATERLOGGING")
    cat_res = await db_session.execute(cat_stmt)
    category = cat_res.scalar_one_or_none()
    if not category:
        category = EventCategory(
            category_code="FLOOD_WATERLOGGING",
            title="Flood / Waterlogging",
            severity_default="HIGH",
            color_hex="#3B82F6",
            icon_name="waves",
        )
        db_session.add(category)
        await db_session.flush()

    # Use isolated timestamp anchor to avoid collision with test database history
    base_time = datetime(2035, 1, 1, 12, 0, tzinfo=timezone.utc)
    base_pt = Point(72.8468, 19.1197)  # Andheri, Mumbai

    # 2. Insert Primary Report 1
    rep1 = WeatherReport(
        tracking_id=f"TRK-2026-{uuid.uuid4().hex[:6].upper()}",
        source_id=source.id,
        category_id=category.id,
        external_id=f"TEST-DUP-{uuid.uuid4().hex[:8]}",
        title="Severe waterlogging near Andheri subway",
        description="Vehicles submerged under 3 feet water.",
        location_name="Andheri subway, Mumbai",
        latitude=19.1197,
        longitude=72.8468,
        geom=from_shape(base_pt, srid=4326),
        occurred_at=base_time,
        verification_status="PENDING",
        credibility_score=0.7,
    )
    db_session.add(rep1)
    await db_session.flush()

    # Evaluate Report 1 (no candidates yet -> DISTINCT)
    res1 = await engine.evaluate_and_cluster(db_session, rep1)
    assert res1.decision == DuplicateDecision.DISTINCT
    assert res1.cluster_id is None
    assert rep1.processing_status == "PROCESSED"
    assert rep1.verification_status == "PENDING"  # Verification status preserved

    # 3. Insert Duplicate Report 2 (100m away, 15m later)
    pt2 = Point(72.8475, 19.1202)
    rep2 = WeatherReport(
        tracking_id=f"TRK-2026-{uuid.uuid4().hex[:6].upper()}",
        source_id=source.id,
        category_id=category.id,
        external_id=f"TEST-DUP-{uuid.uuid4().hex[:8]}",
        title="Knee deep water outside Andheri station",
        description="Subway completely inundated and traffic stopped.",
        location_name="Andheri, Mumbai",
        latitude=19.1202,
        longitude=72.8475,
        geom=from_shape(pt2, srid=4326),
        occurred_at=base_time + timedelta(minutes=15),
        verification_status="PENDING",
        credibility_score=0.7,
    )
    db_session.add(rep2)
    await db_session.flush()

    # Evaluate Report 2 -> Creates Cluster
    res2 = await engine.evaluate_and_cluster(db_session, rep2)
    assert res2.decision == DuplicateDecision.DUPLICATE
    assert res2.cluster_id is not None
    assert rep2.processing_status == "PROCESSED"
    # Verification status remains PENDING for human queue review
    assert rep2.verification_status == "PENDING"

    # Verify cluster in DB
    c_stmt = select(DuplicateCluster).where(DuplicateCluster.id == res2.cluster_id)
    c_res = await db_session.execute(c_stmt)
    cluster = c_res.scalar_one()
    assert cluster.primary_report_id == rep1.id
    assert cluster.member_count == 2

    # 4. Insert Duplicate Report 3 (joins same cluster)
    pt3 = Point(72.8470, 19.1200)
    rep3 = WeatherReport(
        tracking_id=f"TRK-2026-{uuid.uuid4().hex[:6].upper()}",
        source_id=source.id,
        category_id=category.id,
        external_id=f"TEST-DUP-{uuid.uuid4().hex[:8]}",
        title="Waterlogging around Andheri station",
        description="Water accumulation near railway track.",
        location_name="Andheri station",
        latitude=19.1200,
        longitude=72.8470,
        geom=from_shape(pt3, srid=4326),
        occurred_at=base_time + timedelta(minutes=30),
        verification_status="PENDING",
        credibility_score=0.7,
    )
    db_session.add(rep3)
    await db_session.flush()

    res3 = await engine.evaluate_and_cluster(db_session, rep3)
    assert res3.decision == DuplicateDecision.DUPLICATE
    assert res3.cluster_id == cluster.id
    assert rep3.processing_status == "PROCESSED"
    assert rep3.verification_status == "PENDING"

    # Check updated member count
    assert cluster.member_count == 3

    # 5. Insert Distinct Report 4 (800km away in Bengaluru) -> DISTINCT
    pt4 = Point(77.5946, 12.9716)  # Bengaluru
    rep4 = WeatherReport(
        tracking_id=f"TRK-2026-{uuid.uuid4().hex[:6].upper()}",
        source_id=source.id,
        category_id=category.id,
        external_id=f"TEST-DUP-{uuid.uuid4().hex[:8]}",
        title="Bengaluru Whitefield waterlogging",
        description="Rain in Bengaluru.",
        location_name="Whitefield, Bengaluru",
        latitude=12.9716,
        longitude=77.5946,
        geom=from_shape(pt4, srid=4326),
        occurred_at=base_time + timedelta(minutes=10),
        verification_status="PENDING",
        credibility_score=0.7,
    )
    db_session.add(rep4)
    await db_session.flush()

    res4 = await engine.evaluate_and_cluster(db_session, rep4)
    assert res4.decision == DuplicateDecision.DISTINCT
    assert res4.cluster_id is None
    assert rep4.processing_status == "PROCESSED"
    assert rep4.verification_status == "PENDING"

    # 6. Verify original reports remain intact (NEVER deleted or physically merged)
    all_reports_stmt = select(WeatherReport).where(
        WeatherReport.id.in_([rep1.id, rep2.id, rep3.id, rep4.id])
    )
    all_res = await db_session.execute(all_reports_stmt)
    persisted_reports = all_res.scalars().all()
    assert len(persisted_reports) == 4


def test_spatial_safety_invariant_distinct_on_exceeded_radius():
    """Safety Invariant A: 100% text match + distance > 2.5km MUST be DISTINCT."""
    scorer = DuplicateScorer()
    res = scorer.score_pair(
        report_a_id=uuid.uuid4(),
        report_b_id=uuid.uuid4(),
        title_a="Severe flash flooding in underpass",
        title_b="Severe flash flooding in underpass",
        desc_a="Water 4 feet deep",
        desc_b="Water 4 feet deep",
        cat_a="FLOOD_WATERLOGGING",
        cat_b="FLOOD_WATERLOGGING",
        lat_a=19.1197,
        lon_a=72.8468,  # Andheri
        lat_b=19.1550,
        lon_b=72.8468,  # ~3.9km away (> 2.5km)
        time_a=datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        time_b=datetime(2026, 8, 29, 10, 5, tzinfo=timezone.utc),
    )
    assert res.decision == DuplicateDecision.DISTINCT
    assert "Distance" in res.explanation


def test_temporal_safety_invariant_distinct_on_exceeded_window():
    """Safety Invariant B: 100% text match + same coords + time delta > 3h MUST be DISTINCT."""
    scorer = DuplicateScorer()
    res = scorer.score_pair(
        report_a_id=uuid.uuid4(),
        report_b_id=uuid.uuid4(),
        title_a="Severe flash flooding in underpass",
        title_b="Severe flash flooding in underpass",
        desc_a="Water 4 feet deep",
        desc_b="Water 4 feet deep",
        cat_a="FLOOD_WATERLOGGING",
        cat_b="FLOOD_WATERLOGGING",
        lat_a=19.1197,
        lon_a=72.8468,
        lat_b=19.1197,
        lon_b=72.8468,
        time_a=datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc),
        time_b=datetime(2026, 8, 29, 13, 0, tzinfo=timezone.utc),  # 5 hours later (> 3h)
    )
    assert res.decision == DuplicateDecision.DISTINCT
    assert "Time delta" in res.explanation


def test_missing_signal_conservatism_never_auto_duplicates():
    """Safety Invariant C: 100% text match + missing coords MUST NEVER be confirmed DUPLICATE."""
    scorer = DuplicateScorer()
    res = scorer.score_pair(
        report_a_id=uuid.uuid4(),
        report_b_id=uuid.uuid4(),
        title_a="Severe flash flooding in underpass",
        title_b="Severe flash flooding in underpass",
        desc_a="Water 4 feet deep",
        desc_b="Water 4 feet deep",
        cat_a="FLOOD_WATERLOGGING",
        cat_b="FLOOD_WATERLOGGING",
        lat_a=None,
        lon_a=None,
        lat_b=None,
        lon_b=None,
        time_a=datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc),
        time_b=datetime(2026, 8, 29, 10, 5, tzinfo=timezone.utc),
    )
    assert res.decision != DuplicateDecision.DUPLICATE
    assert res.decision == DuplicateDecision.POSSIBLE_MATCH
    assert "incomplete" in res.explanation


@pytest.mark.asyncio
async def test_cluster_assignment_idempotency_and_conflict_safety(db_session: AsyncSession):
    """Safety Invariant D & E: Repeated clustering is idempotent and conflict-safe."""
    engine = IncidentClusteringEngine()

    src_stmt = select(Source).where(Source.source_code == "CITIZEN")
    src_res = await db_session.execute(src_stmt)
    source = src_res.scalar_one_or_none()
    if not source:
        source = Source(
            source_code="CITIZEN",
            name="Citizen Report Ingestion",
            source_type="CITIZEN",
            base_trust_score=0.5,
            is_active=True,
        )
        db_session.add(source)
        await db_session.flush()

    cat_stmt = select(EventCategory).where(EventCategory.category_code == "FLOOD_WATERLOGGING")
    cat_res = await db_session.execute(cat_stmt)
    category = cat_res.scalar_one_or_none()
    if not category:
        category = EventCategory(
            category_code="FLOOD_WATERLOGGING",
            title="Flood / Waterlogging",
            severity_default="HIGH",
            color_hex="#3B82F6",
            icon_name="waves",
        )
        db_session.add(category)
        await db_session.flush()

    base_time = datetime(2036, 1, 1, 12, 0, tzinfo=timezone.utc)
    base_pt = Point(72.8468, 19.1197)

    rep_primary = WeatherReport(
        tracking_id=f"TRK-2026-{uuid.uuid4().hex[:6].upper()}",
        source_id=source.id,
        category_id=category.id,
        external_id=f"TEST-DUP-{uuid.uuid4().hex[:8]}",
        title="Inundated subway at Andheri",
        description="Water accumulation.",
        location_name="Andheri",
        latitude=19.1197,
        longitude=72.8468,
        geom=from_shape(base_pt, srid=4326),
        occurred_at=base_time,
        verification_status="PENDING",
        credibility_score=0.7,
    )
    db_session.add(rep_primary)
    await db_session.flush()

    rep_duplicate = WeatherReport(
        tracking_id=f"TRK-2026-{uuid.uuid4().hex[:6].upper()}",
        source_id=source.id,
        category_id=category.id,
        external_id=f"TEST-DUP-{uuid.uuid4().hex[:8]}",
        title="Subway inundated at Andheri station",
        description="Water accumulation.",
        location_name="Andheri",
        latitude=19.1200,
        longitude=72.8470,
        geom=from_shape(Point(72.8470, 19.1200), srid=4326),
        occurred_at=base_time + timedelta(minutes=5),
        verification_status="PENDING",
        credibility_score=0.7,
    )
    db_session.add(rep_duplicate)
    await db_session.flush()

    # Initial clustering
    res1 = await engine.evaluate_and_cluster(db_session, rep_duplicate)
    assert res1.decision == DuplicateDecision.DUPLICATE
    cluster_id = res1.cluster_id
    assert cluster_id is not None

    # Repeated clustering evaluation of the same duplicate report
    res2 = await engine.evaluate_and_cluster(db_session, rep_duplicate)
    assert res2.decision == DuplicateDecision.DUPLICATE
    assert res2.cluster_id == cluster_id

    # Verify DuplicateMember count in database is exactly 1 (not duplicated)
    from app.models.duplicate import DuplicateMember

    m_stmt = select(DuplicateMember).where(DuplicateMember.cluster_id == cluster_id)
    m_res = await db_session.execute(m_stmt)
    members = m_res.scalars().all()
    assert len(members) == 1
    assert members[0].report_id == rep_duplicate.id
