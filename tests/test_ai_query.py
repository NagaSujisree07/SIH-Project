import pytest
from httpx import AsyncClient

from app.schemas.query import QueryRequest
from app.services.ai.deterministic_parser import DeterministicParser
from app.services.ai.service import FloatChatAIService


@pytest.mark.asyncio
async def test_nlp_temperature_query():
    """Test natural language parsing for temperature queries."""
    prompt = "Show temperature for ARGO_001 in the upper 100 meters"
    req, ctx = await FloatChatAIService.parse_query(prompt)

    assert req.float_ids == ["ARGO_001"]
    assert req.depth_range == {"min": 0.0, "max": 100.0}
    assert "temperature_C" in req.parameters
    assert ctx["status"] == "success"
    assert ctx["parser_used"] == "deterministic_rules"


@pytest.mark.asyncio
async def test_nlp_salinity_query():
    """Test natural language parsing for salinity and basin queries."""
    prompt = "Show salinity measurements in the Arabian Sea"
    req, ctx = await FloatChatAIService.parse_query(prompt)

    assert "salinity" in req.parameters
    assert req.bounding_box is not None
    assert req.bounding_box.min_lat == 8.0
    assert req.bounding_box.max_lat == 25.0
    assert ctx["status"] == "success"


@pytest.mark.asyncio
async def test_nlp_depth_range_query():
    """Test natural language parsing for specific depth ranges."""
    prompt = "Find ocean observations between 50 and 200 meters"
    req, ctx = await FloatChatAIService.parse_query(prompt)

    assert req.depth_range == {"min": 50.0, "max": 200.0}
    assert ctx["status"] == "success"


@pytest.mark.asyncio
async def test_nlp_float_id_query():
    """Test natural language parsing extracting float IDs in various formats."""
    prompt = "Retrieve all sensor profiles from float ARGO_002"
    req, ctx = await FloatChatAIService.parse_query(prompt)

    assert req.float_ids == ["ARGO_002"]
    assert ctx["status"] == "success"


@pytest.mark.asyncio
async def test_nlp_date_range_query():
    """Test natural language parsing for date range boundaries."""
    prompt = "Show oxygen measurements from ARGO_001 between August 1 and August 5, 2026"
    req, ctx = await FloatChatAIService.parse_query(prompt)

    assert req.float_ids == ["ARGO_001"]
    assert "dissolved_oxygen_umol_kg" in req.parameters
    assert req.start_date is not None
    assert req.end_date is not None
    assert req.start_date.year == 2026
    assert req.start_date.month == 8
    assert req.start_date.day == 1
    assert req.end_date.year == 2026
    assert req.end_date.month == 8
    assert req.end_date.day == 5
    assert ctx["status"] == "success"


@pytest.mark.asyncio
async def test_nlp_spatial_proximity_query():
    """Test natural language parsing for lat/lon coordinate radius queries."""
    prompt = "Find floats near 42.0 latitude and -42.0 longitude within 500 km"
    req, ctx = await FloatChatAIService.parse_query(prompt)

    assert req.bounding_box is not None
    assert req.bounding_box.min_lat < 42.0 < req.bounding_box.max_lat
    assert req.bounding_box.min_lon < -42.0 < req.bounding_box.max_lon
    assert ctx["status"] == "success"


@pytest.mark.asyncio
async def test_nlp_combined_filters_query():
    """Test complex combined query with float, depth, date, and multiple parameters."""
    prompt = (
        "Show temperature, salinity and chlorophyll for ARGO_001 in top 50m "
        "between August 1, 2026 and August 10, 2026"
    )
    req, ctx = await FloatChatAIService.parse_query(prompt)

    assert req.float_ids == ["ARGO_001"]
    assert req.depth_range == {"min": 0.0, "max": 50.0}
    assert "temperature_C" in req.parameters
    assert "salinity" in req.parameters
    assert "chlorophyll_mg_m3" in req.parameters
    assert req.start_date is not None
    assert req.end_date is not None
    assert ctx["status"] == "success"


@pytest.mark.asyncio
async def test_nlp_unsupported_ambiguous_query():
    """Test handling of unsupported/ambiguous non-oceanographic queries."""
    prompt = "What is the capital of France and how to bake a chocolate cake?"
    req, ctx = await FloatChatAIService.parse_query(prompt)

    assert ctx["status"] == "ambiguous_or_unsupported"
    assert "Could not identify" in ctx["explanation"]


@pytest.mark.asyncio
async def test_nlp_operation_without_api_key():
    """Verify parser works 100% deterministically without external LLM API keys."""
    # Ensure DeterministicParser directly produces complete valid schema
    prompt = "Show nitrate and pH for ARGO_003 deeper than 100 meters"
    req, ctx = DeterministicParser.parse(prompt)

    assert req.float_ids == ["ARGO_003"]
    assert req.depth_range == {"min": 100.0}
    assert "nitrate_umol_kg" in req.parameters
    assert "pH" in req.parameters
    assert ctx["parser_used"] == "deterministic_rules"
    assert ctx["status"] == "success"


@pytest.mark.asyncio
async def test_nlp_via_api_endpoint_e2e(async_client: AsyncClient):
    """End-to-end integration test of POST /query using natural language prompt."""
    payload = {
        "natural_language_prompt": "Show temperature and salinity for ARGO_001 in upper 100 meters",
        "limit": 5,
    }
    response = await async_client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["total_matched"] >= 1
    assert len(data["data"]) >= 1
    assert data["ai_context"] is not None
    assert data["ai_context"]["status"] == "success"
    assert data["ai_context"]["received_prompt"] == payload["natural_language_prompt"]

    # Verify returned records match the parsed criteria
    for item in data["data"]:
        assert item["float_id"] == "ARGO_001"
        assert item["depth_m"] <= 100.0
        assert "temperature_C" in item["parameters"]
        assert "salinity" in item["parameters"]
