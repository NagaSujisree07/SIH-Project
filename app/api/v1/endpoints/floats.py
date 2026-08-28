from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.float import Float
from app.models.profile import Profile
from app.schemas.common import PaginatedResponse
from app.schemas.floats import FloatPlaceholder, FloatTrajectoryPoint, FloatTrajectoryResponse

router = APIRouter(tags=["Floats"])


@router.get(
    "/floats",
    response_model=PaginatedResponse[FloatPlaceholder],
    summary="List ARGO Floats",
    description="Retrieve a paginated list of ARGO oceanographic floats.",
)
async def list_floats(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    status: Optional[str] = Query(None, description="Reserved for future status filtering"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[FloatPlaceholder]:

    count_result = await db.execute(
        select(func.count()).select_from(Float)
    )
    total = count_result.scalar_one()

    offset = (page - 1) * page_size

    result = await db.execute(
        select(Float)
        .order_by(Float.id)
        .offset(offset)
        .limit(page_size)
    )
    floats = result.scalars().all()

    items = []

    for float_obj in floats:
        profile_result = await db.execute(
            select(Profile)
            .where(Profile.float_id == float_obj.id)
            .order_by(Profile.date.desc(), Profile.cycle_number.desc())
            .limit(1)
        )
        latest_profile = profile_result.scalar_one_or_none()

        last_location = None
        last_reported_at = None

        if latest_profile:
            last_location = {
                "latitude": latest_profile.latitude,
                "longitude": latest_profile.longitude,
            }
            last_reported_at = latest_profile.date

        items.append(
            FloatPlaceholder(
                id=float_obj.id,
                wmo_number=None,
                status=None,
                last_location=last_location,
                last_reported_at=last_reported_at,
                metadata={
                    "region": float_obj.region,
                },
            )
        )

    total_pages = (total + page_size - 1) // page_size if total else 0

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


@router.get(
    "/floats/{id}",
    response_model=FloatPlaceholder,
    summary="Get Float Details",
    description="Retrieve detailed metadata for a specific ARGO float.",
)
async def get_float_by_id(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> FloatPlaceholder:

    result = await db.execute(
        select(Float).where(Float.id == id)
    )
    float_obj = result.scalar_one_or_none()

    if float_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Float with ID '{id}' not found.",
        )

    profile_result = await db.execute(
        select(Profile)
        .where(Profile.float_id == float_obj.id)
        .order_by(Profile.date.desc(), Profile.cycle_number.desc())
        .limit(1)
    )
    latest_profile = profile_result.scalar_one_or_none()

    last_location = None
    last_reported_at = None

    if latest_profile:
        last_location = {
            "latitude": latest_profile.latitude,
            "longitude": latest_profile.longitude,
        }
        last_reported_at = latest_profile.date

    return FloatPlaceholder(
        id=float_obj.id,
        wmo_number=None,
        status=None,
        last_location=last_location,
        last_reported_at=last_reported_at,
        metadata={
            "region": float_obj.region,
        },
    )


@router.get(
    "/floats/{id}/trajectory",
    response_model=FloatTrajectoryResponse,
    summary="Get Float Trajectory",
    description="Retrieve chronological trajectory points for a specific float.",
)
async def get_float_trajectory(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> FloatTrajectoryResponse:

    float_result = await db.execute(
        select(Float).where(Float.id == id)
    )
    float_obj = float_result.scalar_one_or_none()

    if float_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Float with ID '{id}' not found.",
        )

    result = await db.execute(
        select(Profile)
        .where(Profile.float_id == id)
        .order_by(Profile.date.asc(), Profile.cycle_number.asc())
    )
    profiles = result.scalars().all()

    trajectory = [
        FloatTrajectoryPoint(
            cycle_number=profile.cycle_number,
            latitude=profile.latitude,
            longitude=profile.longitude,
            timestamp=None,
            extra_properties={
                "date": profile.date.isoformat(),
            },
        )
        for profile in profiles
    ]

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        point.longitude,
                        point.latitude,
                    ],
                },
                "properties": {
                    "cycle_number": point.cycle_number,
                    "timestamp": point.timestamp.isoformat()
                    if point.timestamp
                    else None,
                    **point.extra_properties,
                },
            }
            for point in trajectory
        ],
    }

    return FloatTrajectoryResponse(
        float_id=id,
        total_points=len(trajectory),
        trajectory=trajectory,
        geojson=geojson,
    )