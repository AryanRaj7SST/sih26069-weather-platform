"""Shared pytest fixtures for the weather platform test suite."""

import pytest_asyncio
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


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
