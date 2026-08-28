from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.bgc_measurement import BGCMeasurement
from app.models.float import Float
from app.models.measurement import Measurement
from app.models.profile import Profile
from app.schemas.query import QueryRequest, QueryResponse

router = APIRouter(tags=["Query & AI Integration"])

# Parameter name alias mapping for flexible querying
PARAM_MAP: Dict[str, str] = {
    "temp": "temperature_C",
    "temperature": "temperature_C",
    "temperature_c": "temperature_C",
    "temperature_C": "temperature_C",
    "psal": "salinity",
    "salinity": "salinity",
    "sal": "salinity",
    "pres": "pressure_dbar",
    "pressure": "pressure_dbar",
    "pressure_dbar": "pressure_dbar",
    "depth": "depth_m",
    "depth_m": "depth_m",
    "density": "density_kg_m3",
    "density_kg_m3": "density_kg_m3",
    "doxy": "dissolved_oxygen_umol_kg",
    "dissolved_oxygen": "dissolved_oxygen_umol_kg",
    "dissolved_oxygen_umol_kg": "dissolved_oxygen_umol_kg",
    "doxy_sat": "oxygen_saturation_pct",
    "oxygen_saturation": "oxygen_saturation_pct",
    "oxygen_saturation_pct": "oxygen_saturation_pct",
    "chla": "chlorophyll_mg_m3",
    "chlorophyll": "chlorophyll_mg_m3",
    "chlorophyll_mg_m3": "chlorophyll_mg_m3",
    "nitrate": "nitrate_umol_kg",
    "nitrate_umol_kg": "nitrate_umol_kg",
    "ph": "pH",
    "pH": "pH",
    "par": "PAR_umol_m2_s",
    "par_umol_m2_s": "PAR_umol_m2_s",
    "PAR_umol_m2_s": "PAR_umol_m2_s",
}


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Multi-Criteria ARGO Query (AI-Ready)",
    description=(
        "Deterministic parametric query engine supporting spatial bounding-box, temporal, "
        "depth, platform, and parameter filters. Decoupled and ready for future AI/LLM structured query integration."
    ),
)
async def execute_query(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    """
    Execute a dynamic multi-criteria search across ARGO floats, profiles, and physical/BGC measurements.
    """
    filters = []

    # 1. Float ID Filtering
    if request.float_ids:
        # Match against Float table / Profile float_id
        clean_float_ids = [fid.strip() for fid in request.float_ids if fid and fid.strip()]
        if clean_float_ids:
            filters.append(Profile.float_id.in_(clean_float_ids))

    # 2. Spatial Bounding Box Filtering (PostGIS spatial acceleration & coordinate bounding)
    if request.bounding_box:
        bbox = request.bounding_box
        # Coordinate bounds
        filters.append(Profile.latitude >= bbox.min_lat)
        filters.append(Profile.latitude <= bbox.max_lat)
        filters.append(Profile.longitude >= bbox.min_lon)
        filters.append(Profile.longitude <= bbox.max_lon)
        # PostGIS spatial envelope containment (SRID 4326)
        filters.append(
            func.ST_Within(
                Profile.geom,
                func.ST_SetSRID(
                    func.ST_MakeEnvelope(
                        bbox.min_lon,
                        bbox.min_lat,
                        bbox.max_lon,
                        bbox.max_lat,
                    ),
                    4326,
                ),
            )
        )

    # 3. Temporal Date Range Filtering
    if request.start_date:
        start_d = request.start_date.date() if isinstance(request.start_date, datetime) else request.start_date
        filters.append(Profile.date >= start_d)

    if request.end_date:
        end_d = request.end_date.date() if isinstance(request.end_date, datetime) else request.end_date
        filters.append(Profile.date <= end_d)

    # 4. Depth Range Filtering
    if request.depth_range:
        min_depth = (
            request.depth_range.get("min")
            if "min" in request.depth_range
            else request.depth_range.get("min_depth", request.depth_range.get("min_m"))
        )
        max_depth = (
            request.depth_range.get("max")
            if "max" in request.depth_range
            else request.depth_range.get("max_depth", request.depth_range.get("max_m"))
        )

        if min_depth is not None:
            filters.append(Measurement.depth_m >= float(min_depth))
        if max_depth is not None:
            filters.append(Measurement.depth_m <= float(max_depth))

    # 5. Parameter Canonicalization
    canonical_requested_params: Optional[Set[str]] = None
    if request.parameters:
        canonical_requested_params = set()
        for p in request.parameters:
            clean_p = p.strip()
            canonical_name = PARAM_MAP.get(clean_p.lower(), clean_p)
            canonical_requested_params.add(canonical_name)

    # Build Count Query
    count_query = (
        select(func.count(Measurement.id))
        .select_from(Measurement)
        .join(Profile, Measurement.profile_id == Profile.id)
        .join(Float, Profile.float_id == Float.id)
        .outerjoin(BGCMeasurement, BGCMeasurement.measurement_id == Measurement.id)
    )

    if filters:
        count_query = count_query.where(and_(*filters))

    total_matched = (await db.execute(count_query)).scalar_one()

    # Pagination settings
    limit = request.limit if request.limit is not None else 50
    offset = request.offset if request.offset is not None else 0

    # Build Data Query
    data_query = (
        select(Measurement, Profile, Float, BGCMeasurement)
        .join(Profile, Measurement.profile_id == Profile.id)
        .join(Float, Profile.float_id == Float.id)
        .outerjoin(BGCMeasurement, BGCMeasurement.measurement_id == Measurement.id)
    )

    if filters:
        data_query = data_query.where(and_(*filters))

    data_query = (
        data_query
        .order_by(Profile.date.desc(), Profile.id.asc(), Measurement.depth_m.asc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(data_query)
    rows = result.all()

    # Format result records
    data_items: List[Dict[str, Any]] = []

    for measurement, profile, float_obj, bgc in rows:
        # Collect physical parameters
        all_params: Dict[str, Any] = {
            "pressure_dbar": measurement.pressure_dbar,
            "depth_m": measurement.depth_m,
            "temperature_C": measurement.temperature_c,
            "salinity": measurement.salinity,
            "density_kg_m3": measurement.density_kg_m3,
        }

        # Collect BGC parameters if available
        if bgc is not None:
            all_params.update({
                "dissolved_oxygen_umol_kg": bgc.dissolved_oxygen_umol_kg,
                "oxygen_saturation_pct": bgc.oxygen_saturation_pct,
                "chlorophyll_mg_m3": bgc.chlorophyll_mg_m3,
                "nitrate_umol_kg": bgc.nitrate_umol_kg,
                "pH": bgc.ph,
                "PAR_umol_m2_s": bgc.par_umol_m2_s,
            })

        # Filter parameters if requested by user
        if canonical_requested_params is not None:
            filtered_params = {
                k: v for k, v in all_params.items()
                if k in canonical_requested_params
            }
        else:
            filtered_params = all_params

        data_items.append({
            "measurement_id": measurement.id,
            "profile_id": profile.id,
            "float_id": profile.float_id,
            "region": float_obj.region if float_obj else None,
            "cycle_number": profile.cycle_number,
            "date": profile.date.isoformat() if profile.date else None,
            "latitude": profile.latitude,
            "longitude": profile.longitude,
            "depth_m": measurement.depth_m,
            "pressure_dbar": measurement.pressure_dbar,
            "parameters": filtered_params,
        })

    return QueryResponse(
        total_matched=int(total_matched),
        returned_count=len(data_items),
        limit=limit,
        offset=offset,
        data=data_items,
        query_executed={
            "float_ids": request.float_ids,
            "bounding_box": request.bounding_box.model_dump() if request.bounding_box else None,
            "start_date": request.start_date.isoformat() if request.start_date else None,
            "end_date": request.end_date.isoformat() if request.end_date else None,
            "parameters": request.parameters,
            "depth_range": request.depth_range,
            "limit": limit,
            "offset": offset,
        },
        ai_context=(
            {
                "received_prompt": request.natural_language_prompt,
                "status": "ready_for_ai_pipeline",
            }
            if request.natural_language_prompt
            else None
        ),
    )

