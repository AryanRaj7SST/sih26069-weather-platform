from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, status

from app.core.config import settings

router = APIRouter()


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description=(
        "Basic liveness probe that returns service health without requiring external datastores."
    ),
)
async def health_check() -> Dict[str, Any]:
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "environment": settings.ENVIRONMENT,
            "version": "0.1.0",
        },
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
