import math
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.measurement import Measurement
from app.models.bgc_measurement import BGCMeasurement
from app.schemas.common import PaginatedResponse
from app.schemas.measurements import MeasurementPlaceholder

router = APIRouter(tags=["Measurements"])


@router.get(
    "/measurements",
    response_model=PaginatedResponse[MeasurementPlaceholder],
    summary="Get ARGO Measurements",
    description="Retrieve vertical depth slices / sensor measurements (temperature, salinity, pressure, etc.) for profiles.",
)
async def list_measurements(
    profile_id: Optional[str] = Query(
        None,
        description="Filter measurements by profile ID"
    ),
    min_depth: Optional[float] = Query(
        None,
        description="Minimum depth in meters"
    ),
    max_depth: Optional[float] = Query(
        None,
        description="Maximum depth in meters"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(
        100,
        ge=1,
        le=1000,
        description="Items per page"
    ),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[MeasurementPlaceholder]:

    # Build the base query
    query = (
        select(Measurement, BGCMeasurement)
        .outerjoin(
            BGCMeasurement,
            BGCMeasurement.measurement_id == Measurement.id
        )
    )

    # Optional profile filter
    if profile_id is not None:
        try:
            profile_id_int = int(profile_id)
            query = query.where(
                Measurement.profile_id == profile_id_int
            )
        except ValueError:
            return PaginatedResponse(
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0,
                items=[],
            )

    # Optional depth filters
    if min_depth is not None:
        query = query.where(Measurement.depth_m >= min_depth)

    if max_depth is not None:
        query = query.where(Measurement.depth_m <= max_depth)

    # Count matching records
    count_query = select(func.count()).select_from(Measurement)

    if profile_id is not None:
        try:
            profile_id_int = int(profile_id)
            count_query = count_query.where(
                Measurement.profile_id == profile_id_int
            )
        except ValueError:
            return PaginatedResponse(
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0,
                items=[],
            )

    if min_depth is not None:
        count_query = count_query.where(
            Measurement.depth_m >= min_depth
        )

    if max_depth is not None:
        count_query = count_query.where(
            Measurement.depth_m <= max_depth
        )

    total = (await db.execute(count_query)).scalar_one()

    # Pagination
    offset = (page - 1) * page_size

    query = (
        query
        .order_by(
            Measurement.profile_id,
            Measurement.depth_m
        )
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    rows = result.all()

    # Convert database records into API response objects
    items = []

    for measurement, bgc in rows:

        parameters = {
            "pressure_dbar": measurement.pressure_dbar,
            "depth_m": measurement.depth_m,
            "temperature_C": measurement.temperature_c,
            "salinity": measurement.salinity,
            "density_kg_m3": measurement.density_kg_m3,
        }

        if bgc is not None:
            parameters.update({
                "dissolved_oxygen_umol_kg": bgc.dissolved_oxygen_umol_kg,
                "oxygen_saturation_pct": bgc.oxygen_saturation_pct,
                "chlorophyll_mg_m3": bgc.chlorophyll_mg_m3,
                "nitrate_umol_kg": bgc.nitrate_umol_kg,
                "pH": bgc.ph,
                "PAR_umol_m2_s": bgc.par_umol_m2_s,
            })

        items.append(
            MeasurementPlaceholder(
                id=str(measurement.id),
                profile_id=str(measurement.profile_id),
                depth_or_pressure=measurement.depth_m,
                parameters=parameters,
                qc_flags=None,
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