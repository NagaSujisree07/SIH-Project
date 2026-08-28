from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.spatial import NearestFloatsRequest, NearestFloatsResponse

router = APIRouter(tags=["Spatial"])


@router.post(
    "/nearest-floats",
    response_model=NearestFloatsResponse,
    summary="Find Nearest ARGO Floats (PostGIS)",
    description="Finds ARGO floats nearest to a given latitude/longitude using PostGIS.",
)
async def find_nearest_floats(
    request: NearestFloatsRequest,
    db: AsyncSession = Depends(get_db),
) -> NearestFloatsResponse:

    radius_km = request.max_distance_km or 500.0

    query = text("""
        WITH latest_profiles AS (
            SELECT DISTINCT ON (p.float_id)
                p.float_id,
                p.latitude,
                p.longitude,
                p.geom,
                p.date
            FROM profiles p
            ORDER BY p.float_id, p.date DESC, p.cycle_number DESC
        )
        SELECT
            lp.float_id,
            lp.latitude,
            lp.longitude,
            ST_Distance(
                lp.geom::geography,
                ST_SetSRID(
                    ST_MakePoint(:longitude, :latitude),
                    4326
                )::geography
            ) / 1000.0 AS distance_km,
            lp.date AS last_reported_at
        FROM latest_profiles lp
        WHERE ST_DWithin(
            lp.geom::geography,
            ST_SetSRID(
                ST_MakePoint(:longitude, :latitude),
                4326
            )::geography,
            :radius_m
        )
        ORDER BY distance_km
        LIMIT :limit
    """)

    result = await db.execute(
        query,
        {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "radius_m": radius_km * 1000.0,
            "limit": request.limit or 10,
        },
    )

    rows = result.mappings().all()

    results = []

    for row in rows:
        results.append(
            {
                "float_id": row["float_id"],
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "distance_km": float(row["distance_km"]),
                "last_reported_at": (
                    row["last_reported_at"].isoformat()
                    if row["last_reported_at"] is not None
                    else None
                ),
                "extra": {},
            }
        )

    return NearestFloatsResponse(
        query_point={
            "latitude": request.latitude,
            "longitude": request.longitude,
        },
        search_radius_km=radius_km,
        total_found=len(results),
        results=results,
    )