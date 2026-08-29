from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Core Application Settings
    PROJECT_NAME: str = "National Weather Big Data Analytics Platform"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "default-insecure-dev-secret-key-replace-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Primary Database (PostgreSQL + PostGIS)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/weather_platform"
    DATABASE_ECHO: bool = False

    # Cache & Event Streaming (Redis)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Object Storage (MinIO / S3)
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY_ID: str = "minioadmin"
    S3_SECRET_ACCESS_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "weather-media"
    S3_REGION: str = "us-east-1"
    S3_USE_SSL: bool = False
    S3_PRESIGNED_EXPIRY_SECONDS: int = 3600

    # External APIs (Optional in Phase 1)
    DATA_GOV_API_KEY: str = ""
    IMD_API_ENDPOINT: str = "https://mausam.imd.gov.in/api/v1"
    IMD_API_KEY: str = ""

    # AI & Semantic Intelligence (Optional in Phase 1)
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    LLM_PROVIDER: str = "none"
    LLM_API_KEY: str = ""

    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v  # type: ignore
        raise ValueError(v)


settings = Settings()
