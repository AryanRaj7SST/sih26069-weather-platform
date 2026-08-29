import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import pool, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.corroboration import IncidentObservationCorroboration
from app.models.evidence import EvidenceItem, IncidentEvidenceLink
from app.models.observation import WeatherObservation
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


@pytest_asyncio.fixture
async def sample_sources(db_session: AsyncSession):
    """Seed test sources for observations and evidence."""
    cwc_src = await db_session.execute(select(Source).where(Source.source_code == "CWC_TELEMETRY"))
    cwc = cwc_src.scalar_one_or_none()
    if not cwc:
        cwc = Source(
            source_code="CWC_TELEMETRY",
            name="Central Water Commission River Telemetry",
            source_type="GOV_OPEN_DATA",
            base_trust_score=0.92,
        )
        db_session.add(cwc)

    gdelt_src = await db_session.execute(select(Source).where(Source.source_code == "GDELT_NEWS"))
    gdelt = gdelt_src.scalar_one_or_none()
    if not gdelt:
        gdelt = Source(
            source_code="GDELT_NEWS",
            name="GDELT DOC 2.0 Web News",
            source_type="RSS",
            base_trust_score=0.70,
        )
        db_session.add(gdelt)

    citizen_src = await db_session.execute(
        select(Source).where(Source.source_code == "CITIZEN_WEB")
    )
    citizen = citizen_src.scalar_one_or_none()
    if not citizen:
        citizen = Source(
            source_code="CITIZEN_WEB",
            name="Citizen Web Portal",
            source_type="CITIZEN",
            base_trust_score=0.60,
        )
        db_session.add(citizen)

    await db_session.commit()
    await db_session.refresh(cwc)
    await db_session.refresh(gdelt)
    await db_session.refresh(citizen)
    return {"cwc": cwc, "gdelt": gdelt, "citizen": citizen}


@pytest.mark.asyncio
async def test_weather_observation_insertion_and_fields(db_session: AsyncSession, sample_sources):
    """Verify insertion of WeatherObservation with water_level_m and PostGIS geometry."""
    cwc = sample_sources["cwc"]
    point_geom = from_shape(Point(72.8777, 19.0760), srid=4326)
    obs_time = datetime.now(timezone.utc)
    ext_id = f"CWC-OBS-{uuid.uuid4().hex[:8]}"

    obs = WeatherObservation(
        source_id=cwc.id,
        external_id=ext_id,
        station_code="CWC-MUM-001",
        station_name="Mithi River Kurla Gauge",
        geom=point_geom,
        observed_at=obs_time,
        water_level_m=352.45,
        rainfall_mm=18.5,
        raw_metrics={"zero_gauge_rl": 350.0, "mean_sea_level": 350.0, "river": "Mithi"},
    )
    db_session.add(obs)
    await db_session.commit()
    await db_session.refresh(obs)

    assert obs.id is not None
    assert obs.external_id == ext_id
    assert obs.water_level_m == 352.45
    assert obs.rainfall_mm == 18.5
    assert obs.raw_metrics["river"] == "Mithi"
    assert obs.source_id == cwc.id


@pytest.mark.asyncio
async def test_evidence_item_insertion_and_uniqueness(db_session: AsyncSession, sample_sources):
    """Verify EvidenceItem persistence, fields, and unique (source_id, external_id) constraint."""
    gdelt = sample_sources["gdelt"]
    ext_id = f"GDELT-{uuid.uuid4().hex[:12]}"
    now_utc = datetime.now(timezone.utc)

    evidence = EvidenceItem(
        source_id=gdelt.id,
        external_id=ext_id,
        evidence_type="NEWS_ARTICLE",
        title="Severe waterlogging reported near Kurla and Sion railway tracks",
        url="https://example.com/news/mumbai-rains-kurla-flood",
        publisher_domain="example.com",
        language="English",
        published_at=now_utc,
        text_snippet="Continuous heavy downpour in Mumbai causes waterlogging...",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        raw_payload={"sourcecountry": "India", "socialimage": "https://example.com/img.jpg"},
    )
    db_session.add(evidence)
    await db_session.commit()
    await db_session.refresh(evidence)

    assert evidence.id is not None
    assert evidence.external_id == ext_id
    assert evidence.evidence_type == "NEWS_ARTICLE"
    assert evidence.publisher_domain == "example.com"
    assert evidence.source_id == gdelt.id

    # Verify duplicate (source_id, external_id) raises IntegrityError
    dup_evidence = EvidenceItem(
        source_id=gdelt.id,
        external_id=ext_id,
        evidence_type="NEWS_ARTICLE",
        title="Duplicate title",
        url="https://example.com/news/mumbai-rains-kurla-flood",
    )
    db_session.add(dup_evidence)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_incident_evidence_link_lifecycle(db_session: AsyncSession, sample_sources):
    """Verify linking WeatherReport to EvidenceItem with match metadata and unique constraint."""
    citizen = sample_sources["citizen"]
    gdelt = sample_sources["gdelt"]

    # 1. Create a WeatherReport incident
    report = WeatherReport(
        tracking_id=f"RPT-{uuid.uuid4().hex[:8].upper()}",
        source_id=citizen.id,
        title="Severe waterlogging on LBS Marg Kurla",
        description="Water 2 feet deep near Kurla station.",
        severity="HIGH",
        geom=from_shape(Point(72.8777, 19.0760), srid=4326),
        latitude=19.0760,
        longitude=72.8777,
        occurred_at=datetime.now(timezone.utc),
    )
    db_session.add(report)

    # 2. Create an EvidenceItem
    evidence = EvidenceItem(
        source_id=gdelt.id,
        external_id=f"GDELT-{uuid.uuid4().hex[:12]}",
        evidence_type="NEWS_ARTICLE",
        title="Traffic disrupted at Kurla due to waterlogging",
        url="https://example.com/news/kurla-traffic-rains",
        publisher_domain="example.com",
    )
    db_session.add(evidence)
    await db_session.commit()
    await db_session.refresh(report)
    await db_session.refresh(evidence)

    # 3. Create IncidentEvidenceLink
    link = IncidentEvidenceLink(
        report_id=report.id,
        evidence_id=evidence.id,
        link_role="SUPPORTING_EVIDENCE",
        confidence_score=0.88,
        match_explanation={
            "keyword_overlap": ["waterlogging", "Kurla"],
            "spatial_match": "Kurla",
        },
    )
    db_session.add(link)
    await db_session.commit()

    # Query with selectinload to verify relationship loading
    stmt = (
        select(IncidentEvidenceLink)
        .where(IncidentEvidenceLink.id == link.id)
        .options(
            selectinload(IncidentEvidenceLink.report),
            selectinload(IncidentEvidenceLink.evidence),
        )
    )
    result = await db_session.execute(stmt)
    loaded_link = result.scalar_one()

    assert loaded_link.id is not None
    assert loaded_link.confidence_score == 0.88
    assert loaded_link.link_role == "SUPPORTING_EVIDENCE"
    assert loaded_link.report.title == report.title
    assert loaded_link.evidence.title == evidence.title

    # 4. Verify unique constraint (report_id, evidence_id)
    dup_link = IncidentEvidenceLink(
        report_id=report.id,
        evidence_id=evidence.id,
        link_role="MEDIA_REPORT",
    )
    db_session.add(dup_link)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_incident_observation_corroboration_lifecycle_and_cascade(
    db_session: AsyncSession, sample_sources
):
    """Verify IncidentObservationCorroboration lifecycle, constraints, and cascade delete."""
    citizen = sample_sources["citizen"]
    cwc = sample_sources["cwc"]

    # 1. Create a WeatherReport incident
    report = WeatherReport(
        tracking_id=f"RPT-{uuid.uuid4().hex[:8].upper()}",
        source_id=citizen.id,
        title="Mithi river overflowing near bridge",
        severity="SEVERE",
        geom=from_shape(Point(72.8777, 19.0760), srid=4326),
        latitude=19.0760,
        longitude=72.8777,
        occurred_at=datetime.now(timezone.utc),
    )
    db_session.add(report)

    # 2. Create a WeatherObservation
    obs = WeatherObservation(
        source_id=cwc.id,
        external_id=f"CWC-OBS-{uuid.uuid4().hex[:8]}",
        station_code="CWC-MITHI-02",
        station_name="Mithi River Gauge 2",
        geom=from_shape(Point(72.8800, 19.0780), srid=4326),
        observed_at=datetime.now(timezone.utc),
        water_level_m=354.10,
    )
    db_session.add(obs)
    await db_session.commit()
    await db_session.refresh(report)
    await db_session.refresh(obs)

    # 3. Create Corroboration Link
    corrob = IncidentObservationCorroboration(
        report_id=report.id,
        observation_id=obs.id,
        distance_meters=350.5,
        time_delta_seconds=300,
        corroboration_score=0.95,
        corroboration_notes="CWC gauge 350m away recorded 354.10m exceeding warning mark.",
    )
    db_session.add(corrob)
    await db_session.commit()

    corrob_id = corrob.id
    obs_id = obs.id

    # Query with selectinload to verify relationship loading
    stmt = (
        select(IncidentObservationCorroboration)
        .where(IncidentObservationCorroboration.id == corrob_id)
        .options(
            selectinload(IncidentObservationCorroboration.report),
            selectinload(IncidentObservationCorroboration.observation),
        )
    )
    result = await db_session.execute(stmt)
    loaded_corrob = result.scalar_one()

    assert loaded_corrob.id is not None
    assert loaded_corrob.distance_meters == 350.5
    assert loaded_corrob.corroboration_score == 0.95
    assert loaded_corrob.report.title == report.title
    assert loaded_corrob.observation.station_name == "Mithi River Gauge 2"

    # 4. Verify unique constraint (report_id, observation_id)
    dup_corrob = IncidentObservationCorroboration(
        report_id=report.id,
        observation_id=obs_id,
        distance_meters=350.5,
        time_delta_seconds=300,
        corroboration_score=0.95,
    )
    db_session.add(dup_corrob)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    # 5. Verify cascade deletion: deleting report deletes corroboration; keeps observation intact
    await db_session.delete(report)
    await db_session.commit()

    corrob_check = await db_session.execute(
        select(IncidentObservationCorroboration).where(
            IncidentObservationCorroboration.id == corrob_id
        )
    )
    assert corrob_check.scalar_one_or_none() is None

    obs_check = await db_session.execute(
        select(WeatherObservation).where(WeatherObservation.id == obs_id)
    )
    assert obs_check.scalar_one_or_none() is not None
