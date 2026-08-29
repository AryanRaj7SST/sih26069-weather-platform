from app.core.config import Settings


def test_settings_infrastructure_defaults():
    """Verify that default settings configure correct local infrastructure targets."""
    settings = Settings()
    assert "postgresql+asyncpg://" in settings.DATABASE_URL
    assert "weather_platform" in settings.DATABASE_URL
    assert "redis://localhost:6379" in settings.REDIS_URL
    assert settings.S3_ENDPOINT_URL == "http://localhost:9000"
    assert settings.S3_BUCKET_NAME == "weather-media"


def test_settings_custom_infrastructure_env(monkeypatch):
    """Verify that environment variables override infrastructure connection settings."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://custom_user:custom_pass@db-host:5432/custom_db",
    )
    monkeypatch.setenv("REDIS_URL", "redis://redis-host:6380/2")
    monkeypatch.setenv("S3_ENDPOINT_URL", "http://minio-host:9000")
    monkeypatch.setenv("S3_BUCKET_NAME", "custom-bucket")

    settings = Settings()
    expected_db = "postgresql+asyncpg://custom_user:custom_pass@db-host:5432/custom_db"
    assert settings.DATABASE_URL == expected_db
    assert settings.REDIS_URL == "redis://redis-host:6380/2"
    assert settings.S3_ENDPOINT_URL == "http://minio-host:9000"
    assert settings.S3_BUCKET_NAME == "custom-bucket"
