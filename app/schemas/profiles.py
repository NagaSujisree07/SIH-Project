from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProfilePlaceholder(BaseModel):
    """Placeholder profile schema (fields will be finalized once ARGO dataset is provided)."""
    id: str = Field(..., description="Unique profile identifier")
    float_id: str = Field(..., description="Associated float/platform ID")
    cycle_number: Optional[int] = Field(None, description="ARGO cycle number")
    timestamp: Optional[datetime] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    levels_count: Optional[int] = Field(0, description="Total vertical depth levels recorded")
    data_mode: Optional[str] = Field(None, description="Real-time (R) / Delayed (D) / Adjusted (A)")
    measurements_preview: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
