from fastapi import APIRouter

from app.api.v1.endpoints import (
    floats,
    health,
    measurements,
    profiles,
    query,
    spatial,
    statistics,
)

api_router = APIRouter()

# Include all endpoint modules
api_router.include_router(health.router)
api_router.include_router(floats.router)
api_router.include_router(profiles.router)
api_router.include_router(measurements.router)
api_router.include_router(statistics.router)
api_router.include_router(spatial.router)
api_router.include_router(query.router)
