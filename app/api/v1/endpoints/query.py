from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.query import QueryRequest, QueryResponse

router = APIRouter(tags=["Query & AI Integration"])


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Multi-Criteria ARGO Query (AI-Ready)",
    description="Deterministic parametric query engine supporting spatial, temporal, depth, and parameter filters. Decoupled and ready for future AI/LLM structured query integration.",
)
async def execute_query(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    # Deterministic query engine placeholder:
    # When AI integration is added later, the AI layer will parse natural language into
    # QueryRequest or execute queries through this endpoint.
    return QueryResponse(
        total_matched=0,
        returned_count=0,
        data=[],
        query_executed={
            "float_ids": request.float_ids,
            "bounding_box": request.bounding_box.model_dump() if request.bounding_box else None,
            "start_date": request.start_date.isoformat() if request.start_date else None,
            "end_date": request.end_date.isoformat() if request.end_date else None,
            "parameters": request.parameters,
            "depth_range": request.depth_range,
        },
        ai_context={
            "received_prompt": request.natural_language_prompt,
            "status": "ready_for_ai_pipeline"
        } if request.natural_language_prompt else None,
    )
