from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import logger
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    logger.info(f"Database Target: {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")
    yield
    logger.info("Shutting down application and disposing database connection pool...")
    await engine.dispose()
    logger.info("Shutdown complete.")


def create_application() -> FastAPI:
    """Factory function to build the FastAPI application instance."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="FastAPI Backend & PostGIS Data Architecture for ARGO Oceanographic Float Data (SIH Project).",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error processing {request.method} {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "An unexpected internal server error occurred."},
        )

    # Mount routes directly at root (for paths like /health, /floats, /nearest-floats)
    app.include_router(api_router)

    # Also mount under /api/v1 for versioned API consumers
    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app


app = create_application()
