import math
from datetime import datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.profile import Profile
from app.models.measurement import Measurement
from app.models.float import Float
from app.schemas.common import PaginatedResponse
from app.schemas.profiles import ProfilePlaceholder

router = APIRouter(tags=["Profiles"])


@router.get(
    "/profiles",
    response_model=PaginatedResponse[ProfilePlaceholder],
    summary="List ARGO Profiles",
    description="Retrieve a paginated list of ARGO cycle profiles, filterable by float_id and cycle.",
)
async def list_profiles(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    float_id: Optional[str] = Query(
        None,
        description="Filter profiles by float identifier"
    ),
    cycle_number: Optional[int] = Query(
        None,
        description="Filter by cycle number"
    ),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ProfilePlaceholder]:

    # Base query
    query = (
        select(Profile)
        .join(Float, Profile.float_id == Float.id)
    )

    # Filters
    if float_id is not None:
        query = query.where(Profile.float_id == float_id)

    if cycle_number is not None:
        query = query.where(Profile.cycle_number == cycle_number)

    # Count matching profiles
    count_query = select(func.count()).select_from(Profile)

    if float_id is not None:
        count_query = count_query.where(Profile.float_id == float_id)

    if cycle_number is not None:
        count_query = count_query.where(
            Profile.cycle_number == cycle_number
        )

    total = (await db.execute(count_query)).scalar_one()

    # Pagination
    offset = (page - 1) * page_size

    query = (
        query
        .order_by(Profile.id)
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    profiles = result.scalars().all()

    items = []

    for profile in profiles:

        # Count measurements belonging to this profile
        measurement_count_query = select(
            func.count()
        ).select_from(Measurement).where(
            Measurement.profile_id == profile.id
        )

        levels_count = (
            await db.execute(measurement_count_query)
        ).scalar_one()

        # Get a small preview of measurements
        preview_query = (
            select(Measurement)
            .where(Measurement.profile_id == profile.id)
            .order_by(Measurement.depth_m)
            .limit(3)
        )

        preview_result = await db.execute(preview_query)
        preview_measurements = preview_result.scalars().all()

        measurements_preview = []

        for measurement in preview_measurements:
            measurements_preview.append({
                "pressure_dbar": measurement.pressure_dbar,
                "depth_m": measurement.depth_m,
                "temperature_C": measurement.temperature_c,
                "salinity": measurement.salinity,
                "density_kg_m3": measurement.density_kg_m3,
            })

        # Convert profile date into a datetime for the API schema
        timestamp = datetime.combine(
            profile.date,
            time.min
        )

        items.append(
            ProfilePlaceholder(
                id=str(profile.id),
                float_id=profile.float_id,
                cycle_number=profile.cycle_number,
                timestamp=timestamp,
                latitude=profile.latitude,
                longitude=profile.longitude,
                levels_count=levels_count,
                data_mode=None,
                measurements_preview=measurements_preview,
                metadata={
                    "date": str(profile.date)
                },
            )
        )

    total_pages = math.ceil(total / page_size) if total else 0

    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


@router.get(
    "/profiles/{id}",
    response_model=ProfilePlaceholder,
    summary="Get Profile by ID",
    description="Retrieve details and measurement summary for a single profile cycle.",
)
async def get_profile_by_id(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> ProfilePlaceholder:

    # Find the requested profile
    try:
        profile_id = int(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile with ID '{id}' not found.",
        )

    result = await db.execute(
        select(Profile).where(Profile.id == profile_id)
    )

    profile = result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile with ID '{id}' not found.",
        )

    # Count measurements
    measurement_count_query = select(
        func.count()
    ).select_from(Measurement).where(
        Measurement.profile_id == profile.id
    )

    levels_count = (
        await db.execute(measurement_count_query)
    ).scalar_one()

    # Get measurement preview
    preview_query = (
        select(Measurement)
        .where(Measurement.profile_id == profile.id)
        .order_by(Measurement.depth_m)
        .limit(3)
    )

    preview_result = await db.execute(preview_query)
    preview_measurements = preview_result.scalars().all()

    measurements_preview = []

    for measurement in preview_measurements:
        measurements_preview.append({
            "pressure_dbar": measurement.pressure_dbar,
            "depth_m": measurement.depth_m,
            "temperature_C": measurement.temperature_c,
            "salinity": measurement.salinity,
            "density_kg_m3": measurement.density_kg_m3,
        })

    timestamp = datetime.combine(
        profile.date,
        time.min
    )

    return ProfilePlaceholder(
        id=str(profile.id),
        float_id=profile.float_id,
        cycle_number=profile.cycle_number,
        timestamp=timestamp,
        latitude=profile.latitude,
        longitude=profile.longitude,
        levels_count=levels_count,
        data_mode=None,
        measurements_preview=measurements_preview,
        metadata={
            "date": str(profile.date)
        },
    )