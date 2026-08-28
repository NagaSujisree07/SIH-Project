from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MeasurementPlaceholder(BaseModel):
    """Placeholder measurement record (e.g. pressure, temperature, salinity, etc.)."""
    id: Optional[str] = None
    profile_id: str = Field(..., description="Parent profile ID")
    depth_or_pressure: Optional[float] = Field(None, description="Depth in meters or pressure in dbar")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Physical/BGC parameters (temperature, salinity, oxygen, etc.)"
    )
    qc_flags: Optional[Dict[str, int]] = Field(
        None,
        description="Quality control flags (1-9) per parameter"
    )


class MeasurementQueryFilter(BaseModel):
    """Filter parameters for vertical measurement retrieval."""
    profile_id: Optional[str] = None
    min_depth: Optional[float] = None
    max_depth: Optional[float] = None
    parameters: Optional[List[str]] = Field(None, description="List of parameter names to fetch")
