from fastapi import APIRouter

from app.api.v1.health import router as health_router

api_v1_router = APIRouter()

# Register core health router
api_v1_router.include_router(health_router, tags=["Health"])
