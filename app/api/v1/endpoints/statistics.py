from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.float import Float
from app.models.profile import Profile
from app.models.measurement import Measurement
from app.schemas.statistics import OceanStatisticsResponse, ParameterStat


router = APIRouter(tags=["Statistics"])


@router.get(
    "/statistics",
    response_model=OceanStatisticsResponse,
    summary="Get Oceanographic Statistics",
    description=(
        "Retrieve aggregated statistics (min, max, mean, standard deviation) "
        "for ocean variables across time and region."
    ),
)
async def get_statistics(
    min_lat: Optional[float] = Query(
        None,
        ge=-90.0,
        le=90.0,
        description="Bounding box minimum latitude",
    ),
    max_lat: Optional[float] = Query(
        None,
        ge=-90.0,
        le=90.0,
        description="Bounding box maximum latitude",
    ),
    min_lon: Optional[float] = Query(
        None,
        ge=-180.0,
        le=180.0,
        description="Bounding box minimum longitude",
    ),
    max_lon: Optional[float] = Query(
        None,
        ge=-180.0,
        le=180.0,
        description="Bounding box maximum longitude",
    ),
    db: AsyncSession = Depends(get_db),
) -> OceanStatisticsResponse:

    # ---------------------------------------------------------
    # Build the base filtered query
    # ---------------------------------------------------------
    filters = []

    if min_lat is not None:
        filters.append(Profile.latitude >= min_lat)

    if max_lat is not None:
        filters.append(Profile.latitude <= max_lat)

    if min_lon is not None:
        filters.append(Profile.longitude >= min_lon)

    if max_lon is not None:
        filters.append(Profile.longitude <= max_lon)

    # ---------------------------------------------------------
    # Count floats, profiles and measurements
    # ---------------------------------------------------------
    count_query = (
        select(
            func.count(distinct(Float.id)),
            func.count(distinct(Profile.id)),
            func.count(distinct(Measurement.id)),
        )
        .select_from(Measurement)
        .join(Profile, Measurement.profile_id == Profile.id)
        .join(Float, Profile.float_id == Float.id)
    )

    if filters:
        count_query = count_query.where(*filters)

    count_result = await db.execute(count_query)
    total_floats, total_profiles, total_measurements = count_result.one()

    # ---------------------------------------------------------
    # Date range
    # ---------------------------------------------------------
    date_query = (
        select(
            func.min(Profile.date),
            func.max(Profile.date),
        )
        .select_from(Measurement)
        .join(Profile, Measurement.profile_id == Profile.id)
    )

    if filters:
        date_query = date_query.where(*filters)

    date_result = await db.execute(date_query)
    min_date, max_date = date_result.one()

    date_range = None

    if min_date is not None and max_date is not None:
        date_range = {
            "start": min_date.isoformat(),
            "end": max_date.isoformat(),
        }

    # ---------------------------------------------------------
    # Bounding box
    # ---------------------------------------------------------
    bbox_query = (
        select(
            func.min(Profile.latitude),
            func.max(Profile.latitude),
            func.min(Profile.longitude),
            func.max(Profile.longitude),
        )
        .select_from(Measurement)
        .join(Profile, Measurement.profile_id == Profile.id)
    )

    if filters:
        bbox_query = bbox_query.where(*filters)

    bbox_result = await db.execute(bbox_query)
    bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon = bbox_result.one()

    bounding_box = None

    if bbox_min_lat is not None:
        bounding_box = {
            "min_lat": float(bbox_min_lat),
            "max_lat": float(bbox_max_lat),
            "min_lon": float(bbox_min_lon),
            "max_lon": float(bbox_max_lon),
        }

    # ---------------------------------------------------------
    # Oceanographic parameter statistics
    # ---------------------------------------------------------
    parameter_columns = [
        ("pressure_dbar", Measurement.pressure_dbar),
        ("depth_m", Measurement.depth_m),
        ("temperature_C", Measurement.temperature_c),
        ("salinity", Measurement.salinity),
        ("density_kg_m3", Measurement.density_kg_m3),
    ]

    parameters = []

    for parameter_name, column in parameter_columns:

        stat_query = (
            select(
                func.min(column),
                func.max(column),
                func.avg(column),
                func.stddev_pop(column),
                func.count(column),
            )
            .select_from(Measurement)
            .join(Profile, Measurement.profile_id == Profile.id)
        )

        if filters:
            stat_query = stat_query.where(*filters)

        stat_result = await db.execute(stat_query)

        min_value, max_value, mean_value, std_dev, sample_count = (
            stat_result.one()
        )

        parameters.append(
            ParameterStat(
                parameter=parameter_name,
                min_value=float(min_value) if min_value is not None else None,
                max_value=float(max_value) if max_value is not None else None,
                mean_value=float(mean_value) if mean_value is not None else None,
                std_dev=float(std_dev) if std_dev is not None else None,
                sample_count=int(sample_count),
            )
        )

    # ---------------------------------------------------------
    # Return final response
    # ---------------------------------------------------------
    return OceanStatisticsResponse(
        total_floats=int(total_floats),
        total_profiles=int(total_profiles),
        total_measurements=int(total_measurements),
        date_range=date_range,
        bounding_box=bounding_box,
        parameters=parameters,
        metadata={
            "source": "ARGO demo dataset",
            "database": "PostgreSQL + PostGIS",
            "statistics": "Computed directly from database records",
        },
    )