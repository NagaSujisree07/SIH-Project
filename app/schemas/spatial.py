from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NearestFloatsRequest(BaseModel):
    """Request payload for PostGIS ST_DWithin / ST_Distance nearest-float lookup."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Target Latitude (-90 to +90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Target Longitude (-180 to +180)")
    max_distance_km: Optional[float] = Field(500.0, gt=0, description="Search radius in kilometers")
    limit: Optional[int] = Field(10, ge=1, le=100, description="Maximum number of nearest floats to return")


class NearestFloatItem(BaseModel):
    """Result item for nearest float query with calculated geodesic distance."""
    float_id: str
    latitude: float
    longitude: float
    distance_km: float = Field(..., description="Geodesic distance from target coordinate in km")
    last_reported_at: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class NearestFloatsResponse(BaseModel):
    """Response envelope for nearest floats query."""
    query_point: Dict[str, float]
    search_radius_km: Optional[float]
    total_found: int
    results: List[NearestFloatItem] = Field(default_factory=list)
