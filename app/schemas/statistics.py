from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ParameterStat(BaseModel):
    parameter: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    std_dev: Optional[float] = None
    sample_count: int = 0


class OceanStatisticsResponse(BaseModel):
    """Statistics aggregation response across time and spatial bounding boxes."""
    total_floats: int = 0
    total_profiles: int = 0
    total_measurements: int = 0
    date_range: Optional[Dict[str, str]] = None
    bounding_box: Optional[Dict[str, float]] = None
    parameters: List[ParameterStat] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
