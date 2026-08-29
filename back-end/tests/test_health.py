import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_app_imports_and_instantiates():
    """Verify that FastAPI application initializes cleanly."""
    assert app is not None
    assert app.title == settings.PROJECT_NAME


@pytest.mark.asyncio
async def test_root_endpoint():
    """Verify that root endpoint provides basic discovery metadata."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == settings.PROJECT_NAME
        assert data["health"] == "/api/v1/health"


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """Verify that health check endpoint returns 200 without requiring external services."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["data"]["status"] == "healthy"
        assert payload["data"]["service"] == settings.PROJECT_NAME
        assert "timestamp" in payload["meta"]
