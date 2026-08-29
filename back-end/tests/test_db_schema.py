import pytest
import pytest_asyncio
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 - ensures all models are imported and registered in Base.metadata
from app.core.config import settings
from app.db.base import Base


def test_models_metadata_registration():
    """Verify that all 11 core domain models are registered in Base.metadata."""
    expected_tables = {
        "users",
        "sources",
        "event_categories",
        "weather_reports",
        "report_media",
        "weather_observations",
        "evidence_items",
        "incident_evidence_links",
        "incident_observation_corroborations",
        "duplicate_clusters",
        "duplicate_members",
        "verification_events",
        "ingestion_runs",
        "audit_logs",
    }
    registered_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(registered_tables), (
        f"Missing tables in metadata: {expected_tables - registered_tables}"
    )


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


@pytest.mark.asyncio
async def test_database_connection_and_extension(db_session: AsyncSession):
    """Verify async database connection and PostGIS extension presence."""
    result = await db_session.execute(
        text("SELECT extname, extversion FROM pg_extension WHERE extname = 'postgis';")
    )
    row = result.fetchone()
    assert row is not None, "PostGIS extension is not installed in the database."
    assert row[0] == "postgis"


@pytest.mark.asyncio
async def test_postgis_spatial_functionality(db_session: AsyncSession):
    """Verify PostGIS spatial geodesic distance computation between two geographic points."""
    # Distance between Mumbai (72.8777, 19.0760) and Pune (73.8567, 18.5204) in meters
    result = await db_session.execute(
        text(
            "SELECT ST_Distance("
            "ST_SetSRID(ST_Point(72.8777, 19.0760), 4326)::geography, "
            "ST_SetSRID(ST_Point(73.8567, 18.5204), 4326)::geography"
            ") AS dist_meters;"
        )
    )
    distance = result.scalar_one()
    assert distance is not None
    # Mumbai to Pune geodesic distance is ~120 km (115,000m - 130,000m)
    assert 115000 < distance < 130000


@pytest.mark.asyncio
async def test_schema_tables_exist_in_database(db_session: AsyncSession):
    """Verify that all 11 application tables exist in PostgreSQL information_schema."""
    result = await db_session.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' "
            "AND table_name IN ("
            "'users', 'sources', 'event_categories', 'weather_reports', "
            "'report_media', 'weather_observations', 'evidence_items', "
            "'incident_evidence_links', 'incident_observation_corroborations', "
            "'duplicate_clusters', 'duplicate_members', 'verification_events', "
            "'ingestion_runs', 'audit_logs'"
            ");"
        )
    )
    tables = {row[0] for row in result.fetchall()}
    expected = {
        "users",
        "sources",
        "event_categories",
        "weather_reports",
        "report_media",
        "weather_observations",
        "evidence_items",
        "incident_evidence_links",
        "incident_observation_corroborations",
        "duplicate_clusters",
        "duplicate_members",
        "verification_events",
        "ingestion_runs",
        "audit_logs",
    }
    assert expected.issubset(tables), f"Missing tables in PostgreSQL: {expected - tables}"
