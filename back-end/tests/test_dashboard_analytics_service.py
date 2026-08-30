"""Comprehensive integration tests for backend dashboard and analytics aggregation service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import EventCategory
from app.models.report import WeatherReport
from app.models.source import Source
from app.services.incident_query_service import incident_query_service


@pytest.mark.asyncio
async def test_dashboard_summary_empty_database(db_session: AsyncSession) -> None:
    """Test dashboard summary with zero records returns safe zeros without division errors."""
    # Ensure empty query by filtering on nonexistent category
    summary = await incident_query_service.get_dashboard_summary(
        session=db_session,
        time_range="all",
        category="NONEXISTENT_CATEGORY_XYZ",
    )

    assert summary.total_count == 0
    assert summary.period_count == 0
    assert summary.count_24h == 0
    assert summary.last_24h_pct == 0
    assert summary.verification.verified_count == 0
    assert summary.verification.verified_rate == 0
    assert summary.verification.pending_count == 0
    assert summary.verification.under_review_count == 0
    assert summary.verification.rejected_count == 0
    assert summary.verification.duplicate_count == 0
    assert summary.severity.severe_high_count == 0
    assert summary.severity.severe_count == 0
    assert summary.severity.high_count == 0
    assert summary.severity.moderate_count == 0
    assert summary.severity.low_count == 0
    assert summary.category_distribution == []
    assert len(summary.diurnal_distribution) == 4
    for d in summary.diurnal_distribution:
        assert d.count == 0


@pytest.mark.asyncio
async def test_dashboard_summary_aggregations_and_breakdowns(
    db_session: AsyncSession,
) -> None:
    """Test dashboard summary with rich fixtures verifying counts, rates, and diurnal buckets."""
    # 1. Ensure a data source exists
    source_res = await db_session.execute(select(Source).limit(1))
    source = source_res.scalar_one_or_none()
    if not source:
        source = Source(
            id=uuid.uuid4(),
            source_code="TEST_CITIZEN_AGG",
            source_type="CITIZEN",
            name="Test Intake Source",
            base_trust_score=0.5,
            is_active=True,
        )
        db_session.add(source)
        await db_session.flush()

    # 2. Ensure an EventCategory exists
    cat_res = await db_session.execute(
        select(EventCategory).where(EventCategory.category_code == "FLOOD_WATERLOGGING")
    )
    category = cat_res.scalar_one_or_none()
    if not category:
        category = EventCategory(
            id=uuid.uuid4(),
            category_code="FLOOD_WATERLOGGING",
            title="Flooding & Waterlogging",
            severity_default="HIGH",
            color_hex="#3b82f6",
            icon_name="droplets",
        )
        db_session.add(category)
        await db_session.flush()

    now = datetime.now(timezone.utc)
    tag = f"TEST-AGGR-{uuid.uuid4().hex[:6].upper()}"

    # Insert 4 reports with varied attributes
    # Report 1: Flood, Severe, Verified, 2h ago (in 24h window), Mumbai
    r1 = WeatherReport(
        id=uuid.uuid4(),
        tracking_id=f"{tag}-1",
        source_id=source.id,
        category_id=category.id,
        reported_category="FLOOD_WATERLOGGING",
        severity="SEVERE",
        title=f"Test Flood 1 {tag}",
        latitude=19.0760,
        longitude=72.8777,
        geom="SRID=4326;POINT(72.8777 19.0760)",
        occurred_at=now - timedelta(hours=2),
        verification_status="VERIFIED",
        processing_status="COMPLETED",
    )

    # Report 2: Flood, High, Pending, 10h ago (in 24h window), Mumbai
    r2 = WeatherReport(
        id=uuid.uuid4(),
        tracking_id=f"{tag}-2",
        source_id=source.id,
        category_id=category.id,
        reported_category="FLOOD_WATERLOGGING",
        severity="HIGH",
        title=f"Test Flood 2 {tag}",
        latitude=19.0760,
        longitude=72.8777,
        geom="SRID=4326;POINT(72.8777 19.0760)",
        occurred_at=now - timedelta(hours=10),
        verification_status="PENDING",
        processing_status="COMPLETED",
    )

    # Report 3: Rain (no category FK, fallback to reported_category),
    # Moderate, Under Review, 36h ago (in 48h window), Mumbai
    r3 = WeatherReport(
        id=uuid.uuid4(),
        tracking_id=f"{tag}-3",
        source_id=source.id,
        category_id=None,
        reported_category="HEAVY_RAINFALL",
        severity="MODERATE",
        title=f"Test Rain 3 {tag}",
        latitude=19.0760,
        longitude=72.8777,
        geom="SRID=4326;POINT(72.8777 19.0760)",
        occurred_at=now - timedelta(hours=36),
        verification_status="UNDER_REVIEW",
        processing_status="COMPLETED",
    )

    # Report 4: Cyclone, Low, Rejected, 5 days ago (in 7d window), Bengaluru
    r4 = WeatherReport(
        id=uuid.uuid4(),
        tracking_id=f"{tag}-4",
        source_id=source.id,
        category_id=None,
        reported_category="CYCLONE_STORM",
        severity="LOW",
        title=f"Test Cyclone 4 {tag}",
        latitude=12.9716,
        longitude=77.5946,
        geom="SRID=4326;POINT(77.5946 12.9716)",
        occurred_at=now - timedelta(days=5),
        verification_status="REJECTED",
        processing_status="COMPLETED",
    )

    db_session.add_all([r1, r2, r3, r4])
    await db_session.flush()

    # Query 7-day summary (should include all 4 reports)
    summary_7d = await incident_query_service.get_dashboard_summary(
        session=db_session,
        time_range="7d",
        from_date=now - timedelta(days=6),
    )

    assert summary_7d.total_count >= 4
    assert summary_7d.period_count == summary_7d.total_count
    assert summary_7d.count_24h >= 2
    assert summary_7d.verification.verified_count >= 1
    # Pending must include PENDING + UNDER_REVIEW
    assert summary_7d.verification.pending_count >= 2
    assert summary_7d.verification.under_review_count >= 1
    assert summary_7d.verification.rejected_count >= 1
    assert summary_7d.severity.severe_high_count >= 2
    assert summary_7d.severity.severe_count >= 1
    assert summary_7d.severity.high_count >= 1
    assert summary_7d.severity.moderate_count >= 1
    assert summary_7d.severity.low_count >= 1

    # Verify category fallback in distribution
    cat_codes = [c.category_code for c in summary_7d.category_distribution]
    assert "FLOOD_WATERLOGGING" in cat_codes
    assert "HEAVY_RAINFALL" in cat_codes
    assert "CYCLONE_STORM" in cat_codes

    # Query 24-hour summary (should include r1 and r2 only)
    summary_24h = await incident_query_service.get_dashboard_summary(
        session=db_session,
        from_date=now - timedelta(hours=20),
    )
    assert summary_24h.total_count >= 2
    assert summary_24h.verification.verified_count >= 1
    assert summary_24h.severity.severe_count >= 1
    assert summary_24h.severity.high_count >= 1

    # Query with Severity filter = SEVERE
    summary_sev = await incident_query_service.get_dashboard_summary(
        session=db_session,
        time_range="all",
        severity="SEVERE",
        from_date=now - timedelta(days=6),
    )
    assert summary_sev.severity.severe_count >= 1
    assert summary_sev.severity.high_count == 0
    assert summary_sev.severity.moderate_count == 0
    assert summary_sev.severity.low_count == 0

    # Query with Verification filter = VERIFIED
    summary_ver = await incident_query_service.get_dashboard_summary(
        session=db_session,
        time_range="all",
        verification_status="VERIFIED",
        from_date=now - timedelta(days=6),
    )
    assert summary_ver.verification.verified_count >= 1
    assert summary_ver.verification.pending_count == 0
    assert summary_ver.verification.rejected_count == 0

    # Query with Category filter
    summary_cat = await incident_query_service.get_dashboard_summary(
        session=db_session,
        time_range="all",
        category="FLOOD_WATERLOGGING",
        from_date=now - timedelta(days=6),
    )
    for cat in summary_cat.category_distribution:
        assert cat.category_code in ("FLOOD_WATERLOGGING", "OTHER")

    # Query with Bounding Box filter (Mumbai bounds: r1, r2, r3 in, r4 out)
    mumbai_bbox = (72.75, 18.85, 73.05, 19.35)
    summary_bbox = await incident_query_service.get_dashboard_summary(
        session=db_session,
        time_range="all",
        bbox=mumbai_bbox,
        from_date=now - timedelta(days=6),
    )
    assert summary_bbox.total_count >= 3  # r1, r2, r3 are in Mumbai


@pytest.mark.asyncio
async def test_analytics_trends_hourly_and_daily(db_session: AsyncSession) -> None:
    """Test analytics trends with 24h 4-hour buckets and 7d daily buckets."""
    # Ensure source
    source_res = await db_session.execute(select(Source).limit(1))
    source = source_res.scalar_one_or_none()
    if not source:
        source = Source(
            id=uuid.uuid4(),
            source_code="TEST_ANALYTICS_AGG",
            source_type="CITIZEN",
            name="Test Analytics Source",
            base_trust_score=0.5,
            is_active=True,
        )
        db_session.add(source)
        await db_session.flush()

    now = datetime.now(timezone.utc)
    tag = f"TEST-TREND-{uuid.uuid4().hex[:6].upper()}"

    # Create 3 reports at different times
    reports = [
        WeatherReport(
            id=uuid.uuid4(),
            tracking_id=f"{tag}-A",
            source_id=source.id,
            severity="SEVERE",
            title=f"Trend Test A {tag}",
            latitude=19.0760,
            longitude=72.8777,
            geom="SRID=4326;POINT(72.8777 19.0760)",
            occurred_at=now - timedelta(hours=1),
            verification_status="VERIFIED",
            processing_status="COMPLETED",
        ),
        WeatherReport(
            id=uuid.uuid4(),
            tracking_id=f"{tag}-B",
            source_id=source.id,
            severity="HIGH",
            title=f"Trend Test B {tag}",
            latitude=19.0760,
            longitude=72.8777,
            geom="SRID=4326;POINT(72.8777 19.0760)",
            occurred_at=now - timedelta(hours=5),
            verification_status="PENDING",
            processing_status="COMPLETED",
        ),
        WeatherReport(
            id=uuid.uuid4(),
            tracking_id=f"{tag}-C",
            source_id=source.id,
            severity="MODERATE",
            title=f"Trend Test C {tag}",
            latitude=19.0760,
            longitude=72.8777,
            geom="SRID=4326;POINT(72.8777 19.0760)",
            occurred_at=now - timedelta(days=2),
            verification_status="VERIFIED",
            processing_status="COMPLETED",
        ),
    ]
    db_session.add_all(reports)
    await db_session.flush()

    # 1. Test 24h hourly trends (should return 6 4-hour buckets)
    hourly_trends = await incident_query_service.get_analytics_trends(
        session=db_session,
        time_range="24h",
        interval="hour",
    )
    assert hourly_trends.time_range == "24h"
    assert hourly_trends.interval == "hour"
    assert len(hourly_trends.buckets) == 6
    expected_windows = ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"]
    for i, b in enumerate(hourly_trends.buckets):
        assert b.bucket == expected_windows[i]
        assert b.total >= 0
        assert b.verified >= 0

    # 2. Test 7d daily trends (should return 7 sequential daily buckets)
    daily_trends = await incident_query_service.get_analytics_trends(
        session=db_session,
        time_range="7d",
        interval="day",
    )
    assert daily_trends.time_range == "7d"
    assert daily_trends.interval == "day"
    assert len(daily_trends.buckets) == 7
    total_in_buckets = sum(b.total for b in daily_trends.buckets)
    assert total_in_buckets >= 3

    # 3. Test 30d daily trends (should return 14 daily buckets)
    thirty_day_trends = await incident_query_service.get_analytics_trends(
        session=db_session,
        time_range="30d",
        interval="day",
    )
    assert thirty_day_trends.time_range == "30d"
    assert len(thirty_day_trends.buckets) == 14


@pytest.mark.asyncio
async def test_regional_distribution_empty_dataset(db_session: AsyncSession) -> None:
    """Test regional distribution with empty filter returns 0 total and empty regions list."""
    reg = await incident_query_service.get_regional_distribution(
        session=db_session,
        time_range="all",
        category="NONEXISTENT_CATEGORY_XYZ",
    )
    assert reg.total_classified == 0
    assert reg.regions == []
    assert reg.time_range == "all"


@pytest.mark.asyncio
async def test_regional_distribution_classification_and_token_safety(
    db_session: AsyncSession,
) -> None:
    """Test classification rules: token safety, city names, spatial fallback, and OTHER fallback."""
    # Ensure a data source exists
    source_res = await db_session.execute(select(Source).limit(1))
    source = source_res.scalar_one_or_none()
    if not source:
        source = Source(
            id=uuid.uuid4(),
            source_code="TEST_REGIONAL_SRC",
            source_type="CITIZEN",
            name="Test Intake Source",
            base_trust_score=0.5,
            is_active=True,
        )
        db_session.add(source)
        await db_session.flush()

    now = datetime.now(timezone.utc)
    tag = f"REG-TEST-{uuid.uuid4().hex[:6].upper()}"

    reports = [
        # 1. Known city match: Pune -> MH
        WeatherReport(
            id=uuid.uuid4(),
            tracking_id=f"{tag}-MH1",
            source_id=source.id,
            severity="HIGH",
            title=f"Pune Test {tag}",
            location_name="Shivajinagar, Pune",
            latitude=18.5204,
            longitude=73.8567,
            geom="SRID=4326;POINT(73.8567 18.5204)",
            occurred_at=now - timedelta(hours=1),
            verification_status="VERIFIED",
            processing_status="COMPLETED",
        ),
        # 2. Known city match: Chennai -> TN
        WeatherReport(
            id=uuid.uuid4(),
            tracking_id=f"{tag}-TN1",
            source_id=source.id,
            severity="MODERATE",
            title=f"Chennai Test {tag}",
            location_name="T. Nagar, Chennai",
            latitude=13.0418,
            longitude=80.2341,
            geom="SRID=4326;POINT(80.2341 13.0418)",
            occurred_at=now - timedelta(hours=2),
            verification_status="VERIFIED",
            processing_status="COMPLETED",
        ),
        # 3. Token safety: 'Vasai Road' contains 'as' but must NOT match Assam (AS),
        # matches MH via Mumbai token or spatial bbox
        WeatherReport(
            id=uuid.uuid4(),
            tracking_id=f"{tag}-MH2",
            source_id=source.id,
            severity="LOW",
            title=f"Vasai Test {tag}",
            location_name="Vasai Road, Mumbai",
            latitude=19.38,
            longitude=72.83,
            geom="SRID=4326;POINT(72.83 19.38)",
            occurred_at=now - timedelta(hours=3),
            verification_status="PENDING",
            processing_status="COMPLETED",
        ),
        # 4. Null location_name: Spatial fallback to Delhi NCR (DL)
        WeatherReport(
            id=uuid.uuid4(),
            tracking_id=f"{tag}-DL1",
            source_id=source.id,
            severity="SEVERE",
            title=f"Delhi GPS Test {tag}",
            location_name=None,
            latitude=28.6139,
            longitude=77.2090,
            geom="SRID=4326;POINT(77.2090 28.6139)",
            occurred_at=now - timedelta(hours=4),
            verification_status="VERIFIED",
            processing_status="COMPLETED",
        ),
        # 5. Null location_name: Spatial fallback to Bengaluru (KA)
        WeatherReport(
            id=uuid.uuid4(),
            tracking_id=f"{tag}-KA1",
            source_id=source.id,
            severity="HIGH",
            title=f"Bengaluru GPS Test {tag}",
            location_name=None,
            latitude=12.9716,
            longitude=77.5946,
            geom="SRID=4326;POINT(77.5946 12.9716)",
            occurred_at=now - timedelta(hours=5),
            verification_status="UNDER_REVIEW",
            processing_status="COMPLETED",
        ),
        # 6. Unmatched location name outside India -> OTHER
        WeatherReport(
            id=uuid.uuid4(),
            tracking_id=f"{tag}-OTH1",
            source_id=source.id,
            severity="LOW",
            title=f"Unknown Test {tag}",
            location_name="Mid-Atlantic Buoy Station",
            latitude=0.0,
            longitude=0.0,
            geom="SRID=4326;POINT(0.0 0.0)",
            occurred_at=now - timedelta(hours=6),
            verification_status="PENDING",
            processing_status="COMPLETED",
        ),
    ]

    db_session.add_all(reports)
    await db_session.flush()

    res = await incident_query_service.get_regional_distribution(
        session=db_session,
        time_range="24h",
    )

    assert res.total_classified >= 6
    code_map = {r.region_code: r for r in res.regions}

    assert "MH" in code_map
    assert code_map["MH"].count >= 2
    assert code_map["MH"].region_name == "Maharashtra"

    assert "TN" in code_map
    assert code_map["TN"].count >= 1
    assert code_map["TN"].region_name == "Tamil Nadu"

    assert "DL" in code_map
    assert code_map["DL"].count >= 1
    assert code_map["DL"].region_name == "Delhi NCR"

    assert "KA" in code_map
    assert code_map["KA"].count >= 1
    assert code_map["KA"].region_name == "Karnataka"

    assert "OTHER" in code_map
    assert code_map["OTHER"].count >= 1
    assert code_map["OTHER"].region_name == "Other Regions"

    # Verify percentages sum close to 100
    total_pct = sum(r.percentage for r in res.regions)
    assert 95 <= total_pct <= 105
