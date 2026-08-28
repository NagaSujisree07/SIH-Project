import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_floats_list(async_client: AsyncClient):
    """Test GET /floats returns empty paginated list."""
    response = await async_client.get("/floats")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_float_by_id_not_found(async_client: AsyncClient):
    """Test GET /floats/{id} returns 404 placeholder."""
    response = await async_client.get("/floats/2900001")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_float_trajectory(async_client: AsyncClient):
    """Test GET /floats/{id}/trajectory returns empty trajectory."""
    response = await async_client.get("/floats/2900001/trajectory")
    assert response.status_code == 200
    data = response.json()
    assert data["float_id"] == "2900001"
    assert data["total_points"] == 0


@pytest.mark.asyncio
async def test_profiles_list(async_client: AsyncClient):
    """Test GET /profiles returns empty paginated list."""
    response = await async_client.get("/profiles")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_profile_by_id_not_found(async_client: AsyncClient):
    """Test GET /profiles/{id} returns 404 placeholder."""
    response = await async_client.get("/profiles/prof_123")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_measurements_list(async_client: AsyncClient):
    """Test GET /measurements returns empty paginated list."""
    response = await async_client.get("/measurements")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_statistics(async_client: AsyncClient):
    """Test GET /statistics returns base statistics structure."""
    response = await async_client.get("/statistics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_floats"] == 0


@pytest.mark.asyncio
async def test_nearest_floats_endpoint(async_client: AsyncClient):
    """Test POST /nearest-floats accepts lat/lon and returns structured response."""
    payload = {
        "latitude": 15.0,
        "longitude": 75.0,
        "max_distance_km": 500.0,
        "limit": 5
    }
    response = await async_client.post("/nearest-floats", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_found"] == 0
    assert data["query_point"]["latitude"] == 15.0


@pytest.mark.asyncio
async def test_query_endpoint(async_client: AsyncClient):
    """Test POST /query accepts structured query filter."""
    payload = {
        "parameters": ["TEMP", "PSAL"],
        "depth_range": {"min": 0, "max": 500},
        "natural_language_prompt": "Show temperature profiles near Arabian Sea"
    }
    response = await async_client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_matched"] == 0
    assert "ai_context" in data
