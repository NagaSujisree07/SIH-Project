from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """Standard API response envelope."""
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[T] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard pagination wrapper for list endpoints."""
    total: int = Field(..., description="Total number of items matching filter")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(50, description="Items per page")
    total_pages: int = Field(..., description="Total available pages")
    items: List[T] = Field(default_factory=list, description="List of items")


class GeoJSONGeometry(BaseModel):
    """GeoJSON Geometry Object (RFC 7946)."""
    type: str = Field(..., examples=["Point"])
    coordinates: List[float] = Field(..., examples=[[72.8777, 19.0760]], description="[Longitude, Latitude]")


class GeoJSONFeature(BaseModel):
    """GeoJSON Feature Object (RFC 7946)."""
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: Dict[str, Any] = Field(default_factory=dict)


class GeoJSONFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection Object (RFC 7946)."""
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature] = Field(default_factory=list)
