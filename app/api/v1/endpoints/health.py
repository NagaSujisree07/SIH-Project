from fastapi import APIRouter
from app.core.config import settings
from app.db.session import check_db_health
from app.schemas.health import DatabaseHealth, HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="Returns the status of the FastAPI backend and checks database connectivity.",
)
async def health_check() -> HealthResponse:
    db_info = await check_db_health()
    
    return HealthResponse(
        status="healthy",
        project=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database=DatabaseHealth(**db_info),
        components={
            "fastapi": "running",
            "postgis_adapter": "ready",
            "spatial_engine": "ready",
            "ai_integration_layer": "pending_future_integration"
        }
    )
