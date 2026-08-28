import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_floats_list(async_client: AsyncClient):
    """Test GET /floats returns paginated list."""
    response = await async_client.get("/floats")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_float_by_id_found(async_client: AsyncClient):
    """Test GET /floats/{id} returns float metadata."""
    response = await async_client.get("/floats/ARGO_001")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "ARGO_001"
    assert data["metadata"]["region"] is not None


@pytest.mark.asyncio
async def test_float_by_id_not_found(async_client: AsyncClient):
    """Test GET /floats/{id} returns 404 for invalid float ID."""
    response = await async_client.get("/floats/INVALID_FLOAT_9999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_float_trajectory(async_client: AsyncClient):
    """Test GET /floats/{id}/trajectory returns trajectory points and GeoJSON."""
    response = await async_client.get("/floats/ARGO_001/trajectory")
    assert response.status_code == 200
    data = response.json()
    assert data["float_id"] == "ARGO_001"
    assert data["total_points"] >= 1
    assert "geojson" in data
    assert data["geojson"]["type"] == "FeatureCollection"


@pytest.mark.asyncio
async def test_profiles_list(async_client: AsyncClient):
    """Test GET /profiles returns paginated profiles."""
    response = await async_client.get("/profiles")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_profile_by_id(async_client: AsyncClient):
    """Test GET /profiles/{id} returns profile detail."""
    response = await async_client.get("/profiles/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "1"
    assert data["float_id"] == "ARGO_001"
    assert data["levels_count"] >= 1


@pytest.mark.asyncio
async def test_profile_by_id_not_found(async_client: AsyncClient):
    """Test GET /profiles/{id} returns 404 for invalid ID."""
    response = await async_client.get("/profiles/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_measurements_list(async_client: AsyncClient):
    """Test GET /measurements returns paginated measurements."""
    response = await async_client.get("/measurements")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_statistics(async_client: AsyncClient):
    """Test GET /statistics returns aggregated oceanographic statistics."""
    response = await async_client.get("/statistics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_floats"] >= 1
    assert data["total_profiles"] >= 1
    assert data["total_measurements"] >= 1
    assert len(data["parameters"]) >= 1


@pytest.mark.asyncio
async def test_nearest_floats_endpoint(async_client: AsyncClient):
    """Test POST /nearest-floats accepts lat/lon and returns structured response."""
    payload = {
        "latitude": 15.0,
        "longitude": 75.0,
        "max_distance_km": 5000.0,
        "limit": 5
    }
    response = await async_client.post("/nearest-floats", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "total_found" in data
    assert data["query_point"]["latitude"] == 15.0
    assert isinstance(data["results"], list)



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
    assert "total_matched" in data
    assert "returned_count" in data
    assert "data" in data
    assert "query_executed" in data
    assert "ai_context" in data
    assert data["ai_context"]["received_prompt"] == "Show temperature profiles near Arabian Sea"


@pytest.mark.asyncio
async def test_query_no_filters(async_client: AsyncClient):
    """Test POST /query with no filters returns valid paginated structure."""
    response = await async_client.post("/query", json={})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["data"], list)
    assert data["returned_count"] == len(data["data"])
    assert data["limit"] == 50
    assert data["offset"] == 0


@pytest.mark.asyncio
async def test_query_float_id_filter(async_client: AsyncClient):
    """Test POST /query with float_ids filter."""
    payload = {"float_ids": ["ARGO_001", "ARGO_002"]}
    response = await async_client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["query_executed"]["float_ids"] == ["ARGO_001", "ARGO_002"]
    for item in data["data"]:
        assert item["float_id"] in ["ARGO_001", "ARGO_002"]


@pytest.mark.asyncio
async def test_query_date_filter(async_client: AsyncClient):
    """Test POST /query with start_date and end_date temporal filter."""
    payload = {
        "start_date": "2024-01-01T00:00:00",
        "end_date": "2026-12-31T23:59:59",
    }
    response = await async_client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["query_executed"]["start_date"] is not None
    assert data["query_executed"]["end_date"] is not None


@pytest.mark.asyncio
async def test_query_depth_filter(async_client: AsyncClient):
    """Test POST /query with depth_range filter."""
    payload = {"depth_range": {"min": 5.0, "max": 100.0}}
    response = await async_client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    for item in data["data"]:
        assert item["depth_m"] >= 5.0
        assert item["depth_m"] <= 100.0


@pytest.mark.asyncio
async def test_query_bounding_box_filter(async_client: AsyncClient):
    """Test POST /query with spatial bounding box filter."""
    payload = {
        "bounding_box": {
            "min_lat": -30.0,
            "max_lat": 30.0,
            "min_lon": 50.0,
            "max_lon": 100.0,
        }
    }
    response = await async_client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["query_executed"]["bounding_box"] is not None
    for item in data["data"]:
        assert -30.0 <= item["latitude"] <= 30.0
        assert 50.0 <= item["longitude"] <= 100.0


@pytest.mark.asyncio
async def test_query_parameter_filter(async_client: AsyncClient):
    """Test POST /query with parameter alias filtering (TEMP, PSAL)."""
    payload = {"parameters": ["TEMP", "PSAL"]}
    response = await async_client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    for item in data["data"]:
        params = item["parameters"]
        # Only requested parameters should be projected
        assert set(params.keys()).issubset({"temperature_C", "salinity"})


@pytest.mark.asyncio
async def test_query_multiple_filters_combined(async_client: AsyncClient):
    """Test POST /query combining float_ids, bounding_box, depth_range, and parameters."""
    payload = {
        "float_ids": ["ARGO_001"],
        "bounding_box": {
            "min_lat": -90.0,
            "max_lat": 90.0,
            "min_lon": -180.0,
            "max_lon": 180.0,
        },
        "depth_range": {"min": 0, "max": 2000},
        "parameters": ["temp", "psal", "doxy"],
        "limit": 10,
        "offset": 0,
    }
    response = await async_client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["returned_count"] <= 10
    assert data["limit"] == 10
    assert data["offset"] == 0


@pytest.mark.asyncio
async def test_query_pagination(async_client: AsyncClient):
    """Test POST /query pagination with limit and offset."""
    payload1 = {"limit": 2, "offset": 0}
    response1 = await async_client.post("/query", json=payload1)
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["limit"] == 2
    assert data1["offset"] == 0
    assert data1["returned_count"] <= 2

    payload2 = {"limit": 2, "offset": 2}
    response2 = await async_client.post("/query", json=payload2)
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["limit"] == 2
    assert data2["offset"] == 2


@pytest.mark.asyncio
async def test_query_invalid_input_and_edge_cases(async_client: AsyncClient):
    """Test POST /query validation error for invalid latitude and non-existent float."""
    # Invalid latitude > 90
    invalid_payload = {
        "bounding_box": {
            "min_lat": -100.0,
            "max_lat": 95.0,
            "min_lon": 0.0,
            "max_lon": 10.0,
        }
    }
    response = await async_client.post("/query", json=invalid_payload)
    assert response.status_code == 422

    # Non-existent float ID returns 0 matches cleanly
    not_found_payload = {"float_ids": ["NON_EXISTENT_FLOAT_99999"]}
    response_nf = await async_client.post("/query", json=not_found_payload)
    assert response_nf.status_code == 200
    data_nf = response_nf.json()
    assert data_nf["total_matched"] == 0
    assert data_nf["data"] == []


@pytest.mark.asyncio
async def test_query_versioned_endpoint(async_client: AsyncClient):
    """Test POST /api/v1/query endpoint also works as expected."""
    response = await async_client.post("/api/v1/query", json={"limit": 5})
    assert response.status_code == 200
    data = response.json()
    assert "total_matched" in data
    assert data["limit"] == 5

