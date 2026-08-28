from app.schemas.common import (
    BaseResponse,
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    GeoJSONGeometry,
    PaginatedResponse,
)
from app.schemas.floats import (
    FloatPlaceholder,
    FloatTrajectoryPoint,
    FloatTrajectoryResponse,
)
from app.schemas.health import DatabaseHealth, HealthResponse
from app.schemas.measurements import MeasurementPlaceholder, MeasurementQueryFilter
from app.schemas.profiles import ProfilePlaceholder
from app.schemas.query import QueryRequest, QueryResponse, SpatialBoundingBox
from app.schemas.spatial import NearestFloatItem, NearestFloatsRequest, NearestFloatsResponse
from app.schemas.statistics import OceanStatisticsResponse, ParameterStat

__all__ = [
    "BaseResponse",
    "PaginatedResponse",
    "GeoJSONGeometry",
    "GeoJSONFeature",
    "GeoJSONFeatureCollection",
    "HealthResponse",
    "DatabaseHealth",
    "FloatPlaceholder",
    "FloatTrajectoryPoint",
    "FloatTrajectoryResponse",
    "ProfilePlaceholder",
    "MeasurementPlaceholder",
    "MeasurementQueryFilter",
    "NearestFloatsRequest",
    "NearestFloatItem",
    "NearestFloatsResponse",
    "OceanStatisticsResponse",
    "ParameterStat",
    "QueryRequest",
    "QueryResponse",
    "SpatialBoundingBox",
]
