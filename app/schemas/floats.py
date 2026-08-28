from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FloatTrajectoryPoint(BaseModel):
    """Trajectory location point."""
    cycle_number: Optional[int] = None
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    timestamp: Optional[datetime] = None
    extra_properties: Dict[str, Any] = Field(default_factory=dict)


class FloatTrajectoryResponse(BaseModel):
    """Trajectory response for a given float."""
    float_id: str
    total_points: int = 0
    trajectory: List[FloatTrajectoryPoint] = Field(default_factory=list)
    geojson: Optional[Dict[str, Any]] = None


class FloatPlaceholder(BaseModel):
    """Placeholder float summary schema (fields will be finalized once ARGO dataset is provided)."""
    id: str = Field(..., description="Unique float/platform identifier")
    wmo_number: Optional[str] = Field(None, description="WMO float identifier")
    status: Optional[str] = Field(None, description="Active / Inactive")
    last_location: Optional[Dict[str, float]] = None
    last_reported_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
