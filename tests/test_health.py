import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    """Test GET /health endpoint returns 200 OK, database connected, and PostGIS available."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "project" in data
    assert "version" in data
    assert "database" in data
    assert data["database"]["status"] == "connected"
    assert data["database"]["database"] == "argo_db"
    assert data["database"]["postgis_available"] is True
    assert data["database"]["postgis_version"] is not None
    assert "PostgreSQL" in data["database"]["postgres_version"]
    assert data["components"]["fastapi"] == "running"
    assert data["components"]["postgis_adapter"] == "ready"


@pytest.mark.asyncio
async def test_health_check_versioned(async_client: AsyncClient):
    """Test GET /api/v1/health endpoint also works and verifies database connection."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"]["status"] == "connected"
    assert data["database"]["postgis_available"] is True
