from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.reports import router as reports_router

api_v1_router = APIRouter()

# Register endpoint routers
api_v1_router.include_router(health_router, tags=["Health"])
api_v1_router.include_router(reports_router, prefix="/reports", tags=["Reports"])
