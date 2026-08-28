from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class DatabaseHealth(BaseModel):
    status: str = Field(..., examples=["connected"])
    database: Optional[str] = Field(None, examples=["argo_db"])
    postgres_version: Optional[str] = Field(None, examples=["PostgreSQL 16.4"])
    postgis_available: bool = Field(False, description="Whether PostGIS extension is installed and active")
    postgis_version: Optional[str] = Field(None, examples=["3.4.3"])
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["healthy"])
    project: str = Field(..., examples=["ARGO Oceanographic Float Backend"])
    version: str = Field(..., examples=["0.1.0"])
    environment: str = Field(..., examples=["development"])
    database: Optional[DatabaseHealth] = None
    components: Dict[str, str] = Field(
        default_factory=lambda: {
            "fastapi": "running",
            "postgis_adapter": "ready",
            "spatial_engine": "ready",
            "ai_integration_layer": "pending_future_integration"
        }
    )
